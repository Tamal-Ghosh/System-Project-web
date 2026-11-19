"""Development DermFM API: bind to localhost only."""
import os
from contextlib import asynccontextmanager
import logging
import threading
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from dermfm.preprocessing import MAX_BYTES, decode_image, encode_metadata

logger = logging.getLogger(__name__)

def create_app(service_factory=None):
    def configured_service():
        from dermfm.e55_service import E55Service
        return E55Service(os.environ.get('E55_BUNDLE_PATH', '/opt/models/dermfm'))
    @asynccontextmanager
    async def lifespan(app):
        app.state.service = None
        try:
            app.state.service = await run_in_threadpool(service_factory or configured_service)
        except Exception:
            logger.exception("DermFM model unavailable; classification disabled")
        yield
        app.state.service = None
    app = FastAPI(title="DermFM development API", lifespan=lifespan)
    gate = threading.Lock()
    @app.get('/health')
    def health():
        service = getattr(app.state, 'service', None)
        return dict(status='ready' if service else 'unavailable', model_version=service.version if service else None)
    @app.post('/api/v1/analyses')
    async def analyze(image: UploadFile = File(...), age: float = Form(...), sex: str = Form(...), site: str = Form("unknown"), clinical: UploadFile | None = File(None)):
        try: encode_metadata(age, sex, site)
        except ValueError as exc: raise HTTPException(422, str(exc)) from exc
        service = getattr(app.state, 'service', None)
        if service is None: raise HTTPException(503, 'Model unavailable. Complete the backend model setup.')
        if not gate.acquire(blocking=False): raise HTTPException(429, 'Another analysis is running. Try again shortly.')
        try:
            contents = await image.read(MAX_BYTES+1)
            try: decoded = decode_image(contents)
            except ValueError as exc: raise HTTPException(422, str(exc)) from exc
            try:
                if getattr(service, 'requires_clinical', False):
                    try: clinical_image = decode_image(await clinical.read(MAX_BYTES+1)) if clinical is not None else None
                    except ValueError as exc: raise HTTPException(422, str(exc)) from exc
                    return await run_in_threadpool(service.predict, decoded, age, sex, site, clinical_image)
                return await run_in_threadpool(service.predict, decoded, age, sex, site)
            except HTTPException:
                raise
            except Exception as exc:
                logger.exception('Inference failed')
                raise HTTPException(503, 'Classification failed; no result was produced.') from exc
        finally:
            await image.close()
            if clinical is not None:
                await clinical.close()
            gate.release()
    return app

app = create_app()

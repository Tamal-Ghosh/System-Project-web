"""Development E38 API. No authentication/storage yet: bind to localhost only."""
from contextlib import asynccontextmanager
import logging
import threading
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from dermfm.service import InferenceService, Settings
from dermfm.preprocessing import MAX_BYTES, decode_image, encode_metadata
from dermfm.calibration import get_calibration_evidence

logger = logging.getLogger(__name__)

def create_app(service_factory=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.service = None
        try:
            app.state.service = await run_in_threadpool(service_factory or (lambda: InferenceService(Settings.from_env())))
        except Exception:
            logger.exception("E38 model unavailable; classification disabled")
        yield
        app.state.service = None
    app = FastAPI(title="DermaInsight E38 development API", lifespan=lifespan)
    gate = threading.Lock()
    @app.get('/api/v1/model/calibration')
    def calibration_evidence():
        service = getattr(app.state, 'service', None)
        return get_calibration_evidence(service.calibration if service else None)

    @app.get('/health')
    def health():
        service = getattr(app.state, 'service', None)
        return dict(status='ready' if service else 'unavailable', model_version=service.version if service else None)
    @app.post('/api/v1/analyses')
    async def analyze(image: UploadFile = File(...), age: float = Form(...), sex: str = Form(...), site: str = Form("unknown")):
        try: encode_metadata(age, sex, site)
        except ValueError as exc: raise HTTPException(422, str(exc)) from exc
        service = getattr(app.state, 'service', None)
        if service is None: raise HTTPException(503, 'Model unavailable. Complete the backend model setup.')
        if not gate.acquire(blocking=False): raise HTTPException(429, 'Another analysis is running. Try again shortly.')
        try:
            contents = await image.read(MAX_BYTES+1)
            try: decoded = decode_image(contents)
            except ValueError as exc: raise HTTPException(422, str(exc)) from exc
            try: return await run_in_threadpool(service.predict, decoded, age, sex, site)
            except Exception as exc:
                logger.exception('Inference failed')
                raise HTTPException(503, 'Classification failed; no result was produced.') from exc
        finally:
            await image.close()
            gate.release()
    return app

app = create_app()

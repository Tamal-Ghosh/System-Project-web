"""Development E38 API. No authentication/storage yet: bind to localhost only."""
import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
import logging
import os
import threading
import time
import uuid
from functools import partial
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, BackgroundTasks
from starlette.concurrency import run_in_threadpool
from dermfm.service import InferenceService, Settings
from dermfm.preprocessing import MAX_BYTES, decode_image, encode_metadata
from dermfm.loader import CLASSES
from dermfm.explain import explain_analysis, xai_available

logger = logging.getLogger(__name__)

# Asynchronous background job tracking and in-memory cache for XAI
jobs: dict = {}
cache: dict = {}
run_lock = asyncio.Lock()
JOB_TTL = 3600  # 1 hour TTL

def _cleanup_jobs():
    now = time.time()
    for k in [k for k, v in jobs.items() if now - v.get("created", 0) > JOB_TTL]:
        jobs.pop(k, None)

def _xai_cache_key(image_bytes: bytes, age: float, sex: str, site: str,
                   target_class: str | None, fold: int | None,
                   n_steps: int, baseline: str, include_metadata: bool) -> str:
    h = hashlib.sha256()
    h.update(image_bytes)
    meta = {
        "age": age, "sex": sex, "site": site,
        "target_class": target_class, "fold": fold,
        "n_steps": n_steps, "baseline": baseline,
        "include_metadata": include_metadata
    }
    h.update(json.dumps(meta, sort_keys=True).encode())
    return h.hexdigest()

def _run_xai_sync(service, decoded, age, sex, site, target_class, fold, n_steps, baseline, include_metadata, job_id):
    jobs[job_id]["stage"] = "integrated_gradients"
    return explain_analysis(service, decoded, age, sex, site,
                            target_class, fold, n_steps, baseline, include_metadata)

async def _xai_worker(job_id: str, service, decoded, age: float, sex: str, site: str,
                      target_class: str | None, fold: int | None,
                      n_steps: int, baseline: str, include_metadata: bool, key: str):
    async with run_lock:
        jobs[job_id].update(status="running", stage="integrated_gradients")
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                partial(_run_xai_sync, service, decoded, age, sex, site,
                        target_class, fold, n_steps, baseline, include_metadata, job_id)
            )
            if isinstance(result, dict) and result.get("status") == "ok":
                cache[key] = result
                jobs[job_id].update(status="done", stage="done", result=result)
            elif isinstance(result, dict) and result.get("status") == "unavailable":
                jobs[job_id].update(status="failed", stage="failed", error=result.get("reason", "unavailable"))
            else:
                jobs[job_id].update(status="done", stage="done", result=result)
        except Exception as exc:
            logger.exception("XAI job %s failed", job_id)
            jobs[job_id].update(status="failed", stage="failed", error=str(exc))

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
    @app.get('/health')
    def health():
        service = getattr(app.state, 'service', None)
        return dict(status='ready' if service else 'unavailable', model_version=service.version if service else None,
                    capabilities={'xai': ['integrated_gradients', 'metadata_shapley'] if service and xai_available() else [],
                                  'grad_cam': 'not_implemented', 'shap': 'not_implemented', 'attention': 'not_implemented'})
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
    @app.post('/api/v1/explanations', status_code=202)
    async def explain(bg: BackgroundTasks,
                      image: UploadFile = File(...), age: float = Form(...), sex: str = Form(...),
                      site: str = Form("unknown"), target_class: str = Form(None), fold: int = Form(None),
                      method: str = Form("integrated_gradients"), n_steps: int = Form(5),
                      baseline: str = Form("blur"), include_metadata: bool = Form(True)):
        _cleanup_jobs()
        try: encode_metadata(age, sex, site)
        except ValueError as exc: raise HTTPException(422, str(exc)) from exc
        if method != 'integrated_gradients': raise HTTPException(422, 'Unknown explanation method.')
        if target_class is not None and target_class not in CLASSES: raise HTTPException(422, 'Unknown target class.')
        if fold is not None and not 0 <= fold <= 4: raise HTTPException(422, 'Fold must be between 0 and 4.')
        if not 4 <= n_steps <= 50: raise HTTPException(422, 'n_steps must be between 4 and 50.')
        if baseline not in ('blur', 'zero'): raise HTTPException(422, 'Baseline must be blur or zero.')
        service = getattr(app.state, 'service', None)
        if service is None: raise HTTPException(503, 'Model unavailable. Complete the backend model setup.')

        try:
            contents = await image.read(MAX_BYTES+1)
            try: decoded = decode_image(contents)
            except ValueError as exc: raise HTTPException(422, str(exc)) from exc
        finally:
            await image.close()

        key = _xai_cache_key(contents, age, sex, site, target_class, fold, n_steps, baseline, include_metadata)
        job_id = str(uuid.uuid4())

        if key in cache:
            cached_result = cache[key]
            jobs[job_id] = {
                "status": "done",
                "stage": "done",
                "result": cached_result,
                "created": time.time()
            }
            return {"job_id": job_id, "status": "done"}

        jobs[job_id] = {
            "status": "queued",
            "stage": "queued",
            "created": time.time()
        }
        bg.add_task(
            _xai_worker,
            job_id, service, decoded, age, sex, site,
            target_class, fold, n_steps, baseline, include_metadata, key
        )
        return {"job_id": job_id, "status": "queued"}

    @app.get('/api/v1/explanations/{job_id}')
    async def get_explanation(job_id: str):
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        return job
    return app

app = create_app()

"""Development E38 API. No authentication/storage yet: bind to localhost only."""
from contextlib import asynccontextmanager
import logging
import threading
from typing import Literal
from uuid import UUID
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field, field_validator, model_validator
from starlette.concurrency import run_in_threadpool
from dermfm.service import InferenceService, Settings
from dermfm.preprocessing import MAX_BYTES, decode_image, encode_metadata
from database import (
    DatabaseUnavailable,
    check_database_connection,
    create_doctor_assessment,
    list_doctor_assessments,
)

logger = logging.getLogger(__name__)


class ScoreSnapshot(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    score: float = Field(ge=0, le=1)


class PatientMetadataSnapshot(BaseModel):
    age: float = Field(ge=0, le=120)
    sex: str = Field(min_length=1, max_length=40)
    site: str = Field(min_length=1, max_length=80)


class DoctorAssessmentCreate(BaseModel):
    patient_id: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_-]{2,39}$')
    analysis_id: UUID
    model_version: str = Field(min_length=1, max_length=160)
    leading_class: str = Field(min_length=1, max_length=80)
    model_scores: list[ScoreSnapshot]
    patient_metadata: PatientMetadataSnapshot
    decision: Literal['agree', 'disagree', 'unsure']
    confidence: int = Field(ge=1, le=5)
    suspected_diagnosis: str | None = Field(default=None, max_length=200)
    differential_diagnoses: list[str] = Field(default_factory=list, max_length=5)
    clinical_note: str | None = Field(default=None, max_length=2000)
    next_action: Literal[
        'routine_follow_up', 'dermatology_referral', 'biopsy_consideration',
        'additional_assessment', 'other'
    ]

    @field_validator('suspected_diagnosis', 'clinical_note', mode='before')
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator('differential_diagnoses')
    @classmethod
    def clean_differentials(cls, values):
        cleaned = [value.strip() for value in values if value.strip()]
        if len(set(value.casefold() for value in cleaned)) != len(cleaned):
            raise ValueError('Differential diagnoses must be unique')
        if any(len(value) > 200 for value in cleaned):
            raise ValueError('Each differential diagnosis must be at most 200 characters')
        return cleaned


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
    @app.get('/health/database')
    def database_health():
        result = check_database_connection()
        if result['status'] != 'connected':
            raise HTTPException(503, 'Database connection is not available.')
        return result

    @app.get('/health')
    def health():
        service = getattr(app.state, 'service', None)
        return dict(status='ready' if service else 'unavailable', model_version=service.version if service else None)

    @app.post('/api/v1/assessments', status_code=201)
    async def create_assessment(assessment: DoctorAssessmentCreate):
        if len(assessment.model_scores) != 11:
            raise HTTPException(422, 'Assessment must include all eleven model scores.')
        labels = [row.label for row in assessment.model_scores]
        if len(set(labels)) != 11 or assessment.leading_class not in labels:
            raise HTTPException(422, 'Model score labels must be unique and include the leading class.')
        try:
            return await run_in_threadpool(create_doctor_assessment, assessment.model_dump())
        except DatabaseUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get('/api/v1/assessments')
    async def list_assessments(limit: int = Query(default=50, ge=1, le=100)):
        try:
            return await run_in_threadpool(list_doctor_assessments, limit)
        except DatabaseUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc

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

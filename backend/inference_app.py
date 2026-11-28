"""Development DermFM API: bind to localhost only."""
import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from functools import partial
from pathlib import Path
from typing import Literal
from uuid import UUID
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile, BackgroundTasks, Header, Response
from assistant.sessions import CaseSessions
from assistant.class_overviews import PostgresClassOverviews, eligible_overview
from assistant.postgres_storage import PostgresCaseSessions, PostgresChatHistory, AssistantStorageUnavailable, assistant_database_url, storage_health
from assistant.conversation import route_question, parameter_answer, prediction_answer, reason_answer, case_fact_answer, used_citations
from assistant.generator import MockAssistantGenerator
from assistant.gemini import GeminiCaseGenerator, GeminiUnavailable
from assistant.gemini import GeminiEmbeddings
from assistant.ingestion import LocalKnowledgeStore
from assistant.retrieval import HybridRetriever
from assistant.vector_store import PostgresKnowledgeStore
from assistant.history import ChatHistory, build_retrieval_query
from pydantic import BaseModel, Field, field_validator, model_validator
from starlette.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse, JSONResponse
from dermfm.preprocessing import MAX_BYTES, decode_image, encode_metadata
from dermfm.calibration import get_calibration_evidence
from dermfm.loader import CLASSES
from dermfm.explain import explain_analysis, xai_available
from database import (
    DatabaseUnavailable,
    check_database_connection,
    create_doctor_assessment,
    create_prescription,
    delete_doctor_assessment,
    list_doctor_assessments,
    list_prescriptions,
    save_analysis_snapshot,
    update_doctor_assessment,
)
from medicine_catalog import MedicineCatalogUnavailable, suggest_medicines

logger = logging.getLogger(__name__)

# Asynchronous background job tracking and in-memory cache for XAI
jobs: dict = {}
cache: dict = {}
run_lock = asyncio.Lock()
JOB_TTL = 3600

def _cleanup_jobs():
    now = time.time()
    for key in [key for key, value in jobs.items() if now - value.get("created", 0) > JOB_TTL]:
        jobs.pop(key, None)

def _xai_cache_key(image_bytes: bytes, age: float, sex: str, site: str,
                   target_class: str | None, fold: int | None,
                   n_steps: int, baseline: str, include_metadata: bool) -> str:
    digest = hashlib.sha256()
    digest.update(image_bytes)
    metadata = {
        "age": age, "sex": sex, "site": site,
        "target_class": target_class, "fold": fold,
        "n_steps": n_steps, "baseline": baseline,
        "include_metadata": include_metadata
    }
    digest.update(json.dumps(metadata, sort_keys=True).encode())
    return digest.hexdigest()

def _run_xai_sync(service, decoded, age, sex, site, target_class, fold, n_steps, baseline, include_metadata, job_id):
    jobs[job_id]["stage"] = "integrated_gradients"
    return explain_analysis(service, decoded, age, sex, site,
                            target_class, fold, n_steps, baseline, include_metadata)

async def _xai_worker(job_id: str, service, decoded, age: float, sex: str, site: str,
                      target_class: str | None, fold: int | None,
                      n_steps: int, baseline: str, include_metadata: bool, key: str,
                      sessions=None, analysis_id=None, case_token=None):
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
                if sessions is not None and analysis_id:
                    sessions.attach_explanation(analysis_id, case_token, result)
                cache[key] = result
                jobs[job_id].update(status="done", stage="done", result=result)
            elif isinstance(result, dict) and result.get("status") == "unavailable":
                jobs[job_id].update(status="failed", stage="failed", error=result.get("reason", "unavailable"))
            else:
                jobs[job_id].update(status="done", stage="done", result=result)
        except Exception as exc:
            logger.exception("XAI job %s failed", job_id)
            jobs[job_id].update(status="failed", stage="failed", error=str(exc))


class ScoreSnapshot(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    score: float = Field(ge=0, le=1)


class PatientMetadataSnapshot(BaseModel):
    age: float = Field(ge=0, le=120)
    sex: str = Field(min_length=1, max_length=40)
    site: str = Field(min_length=1, max_length=80)


class UncertaintySnapshot(BaseModel):
    normalized_entropy: float = Field(ge=0, le=1)
    top_two_margin: float = Field(ge=0, le=1)


class EnsembleSnapshot(BaseModel):
    member_count: int = Field(ge=1, le=100)
    agreement: float | None = Field(default=None, ge=0, le=1)


class DoctorAssessmentCreate(BaseModel):
    patient_id: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_-]{2,39}$')
    patient_name: str = Field(min_length=2, max_length=120)
    analysis_id: UUID
    model_version: str = Field(min_length=1, max_length=160)
    leading_class: str = Field(min_length=1, max_length=80)
    model_scores: list[ScoreSnapshot]
    patient_metadata: PatientMetadataSnapshot
    image_snapshot: str | None = Field(default=None, max_length=1_500_000, pattern=r'^data:image/(jpeg|png|webp);base64,')
    uncertainty: UncertaintySnapshot
    ensemble: EnsembleSnapshot
    input_policy: str = Field(min_length=1, max_length=240)
    tta: bool
    limitations: list[str] = Field(default_factory=list, max_length=12)
    decision: Literal['agree', 'disagree', 'unsure']
    confidence: int = Field(ge=1, le=5)
    suspected_diagnosis: str | None = Field(default=None, max_length=200)
    differential_diagnoses: list[str] = Field(default_factory=list, max_length=5)
    clinical_note: str | None = Field(default=None, max_length=2000)
    next_action: Literal[
        'routine_follow_up', 'dermatology_referral', 'biopsy_consideration',
        'additional_assessment', 'other'
    ]

    @field_validator('patient_name', 'suspected_diagnosis', 'clinical_note', mode='before')
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class DoctorAssessmentUpdate(BaseModel):
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


class ReportPdfRequest(BaseModel):
    html: str = Field(min_length=1, max_length=2_500_000)
    filename: str = Field(default='skin-lesion-report.pdf', max_length=120)


def _find_headless_browser() -> str | None:
    candidates = [
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    for cmd in ('msedge', 'google-chrome', 'chromium', 'chromium-browser'):
        found = shutil.which(cmd)
        if found:
            return found
    return None


def _render_html_to_pdf(html: str) -> bytes:
    browser = _find_headless_browser()
    if not browser:
        raise RuntimeError('No headless browser available for PDF rendering.')
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        html_path = Path(tmp_dir) / 'report.html'
        pdf_path = Path(tmp_dir) / 'report.pdf'
        profile_dir = Path(tmp_dir) / 'profile'
        html_path.write_text(html, encoding='utf-8')
        result = subprocess.run(
            [
                browser,
                '--headless=new',
                '--disable-gpu',
                '--no-sandbox',
                f'--user-data-dir={profile_dir}',
                '--no-pdf-header-footer',
                f'--print-to-pdf={pdf_path}',
                'file:///' + str(html_path).replace('\\', '/'),
            ],
            capture_output=True,
            text=True,
            timeout=25,
        )
        if result.returncode != 0 or not pdf_path.is_file():
            raise RuntimeError('PDF rendering failed.')
        return pdf_path.read_bytes()

    @field_validator('differential_diagnoses')
    @classmethod
    def clean_differentials(cls, values):
        cleaned = [value.strip() for value in values if value.strip()]
        if len(set(value.casefold() for value in cleaned)) != len(cleaned):
            raise ValueError('Differential diagnoses must be unique')
        if any(len(value) > 200 for value in cleaned):
            raise ValueError('Each differential diagnosis must be at most 200 characters')
        return cleaned


class MedicationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    rxcui: str | None = Field(default=None, pattern=r'^\d+$')
    strength: str = Field(default='', max_length=80)
    formulation: str = Field(default='', max_length=80)
    route: str = Field(default='', max_length=80)
    morning: Literal['0', '¼', '½', '1', '1½', '2']
    noon: Literal['0', '¼', '½', '1', '1½', '2']
    night: Literal['0', '¼', '½', '1', '1½', '2']
    duration: str = Field(min_length=1, max_length=120)
    instructions: str = Field(default='', max_length=500)

    @field_validator('*', mode='before')
    @classmethod
    def strip_medication_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode='after')
    def require_scheduled_dose(self):
        if self.morning == self.noon == self.night == '0':
            raise ValueError('At least one medicine dose time is required')
        return self


class PrescriptionCreate(BaseModel):
    assessment_id: UUID | None = None
    patient_id: str = Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_-]{2,39}$')
    patient_name: str = Field(min_length=2, max_length=120)
    analysis_id: UUID
    model_version: str = Field(min_length=1, max_length=160)
    leading_class: str = Field(min_length=1, max_length=80)
    patient_metadata: PatientMetadataSnapshot
    symptoms: list[str] = Field(default_factory=list, max_length=12)
    allergy_status: Literal['none_known', 'present', 'unknown']
    allergy_details: str | None = Field(default=None, max_length=500)
    medications: list[MedicationCreate] = Field(min_length=1, max_length=10)
    follow_up: str | None = Field(default=None, max_length=500)

    @field_validator('symptoms')
    @classmethod
    def clean_symptoms(cls, values):
        cleaned = [value.strip() for value in values if value.strip()]
        if any(len(value) > 120 for value in cleaned):
            raise ValueError('Each symptom must be at most 120 characters')
        return list(dict.fromkeys(cleaned))

    @field_validator('allergy_details', 'follow_up', mode='before')
    @classmethod
    def strip_optional_text(cls, value):
        return value.strip() or None if isinstance(value, str) else value

    @field_validator('allergy_details')
    @classmethod
    def require_allergy_details(cls, value, info):
        if info.data.get('allergy_status') == 'present' and not value:
            raise ValueError('Allergy details are required when allergies are present')
        return value

class ChatQuery(BaseModel):
    analysis_id: UUID
    question: str = Field(min_length=1, max_length=2000)

    @field_validator('question')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('Question must not be blank')
        return value.strip()


class ChatFeedback(BaseModel):
    analysis_id: UUID
    message_id: UUID
    rating: Literal['helpful', 'unhelpful']


def create_app(service_factory=None):
    def configured_service():
        from dermfm.e55_service import E55Service
        return E55Service(os.environ.get('E55_BUNDLE_PATH', '/opt/models/dermfm'))
    storage_mode=os.getenv('ASSISTANT_STORAGE','local')
    if storage_mode not in ('local','postgres'):raise ValueError('Invalid ASSISTANT_STORAGE')
    online_url=assistant_database_url() if storage_mode=='postgres' else None
    class_overviews=PostgresClassOverviews(online_url) if online_url else None
    case_sessions = PostgresCaseSessions(online_url) if online_url else CaseSessions(path=os.getenv('CASE_SESSION_PATH'))
    provider = os.getenv('ASSISTANT_PROVIDER', 'gemini' if os.getenv('GEMINI_API_KEY') else 'mock')
    if provider not in ('gemini', 'mock'):
        raise ValueError('ASSISTANT_PROVIDER must be gemini or mock')
    generator = GeminiCaseGenerator() if provider == 'gemini' else MockAssistantGenerator()
    knowledge_path = Path(os.getenv('KNOWLEDGE_PATH', str(Path(__file__).with_name('artifacts') / 'assistant-knowledge.sqlite')))
    history = PostgresChatHistory(online_url) if online_url else ChatHistory(os.getenv('CHAT_HISTORY_PATH', str(Path(tempfile.gettempdir()) / 'dermascope-chat-history.sqlite')))
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
    @app.exception_handler(AssistantStorageUnavailable)
    async def assistant_storage_failure(request,exc):
        return JSONResponse(status_code=503,content={'detail':'Online chat storage is temporarily unavailable. Please retry.'})

    @app.get('/api/v1/chat/health')
    @app.get('/health/assistant')
    def assistant_health():
        return storage_health(online_url) if online_url else {'status':'local','storage':'sqlite'}

    from segmentation.routes import segmentation_router
    app.include_router(segmentation_router())
    gate = threading.Lock()
    @app.get('/api/v1/model/reference', response_class=PlainTextResponse)
    def model_reference(version: str = Query(default='e55-multiscale-c769f025f83f3f0f', max_length=100)):
        if version != 'e55-multiscale-c769f025f83f3f0f':
            raise HTTPException(404,'Model reference version not available')
        path=Path(os.getenv('MODEL_REFERENCE_PATH', str(Path(__file__).resolve().parents[1]/'docs'/'assistant-model-reference.md')))
        if not path.is_file(): raise HTTPException(404,'Model reference is unavailable')
        return PlainTextResponse(path.read_text(encoding='utf-8'),headers={'Cache-Control':'no-cache'})

    @app.get('/api/v1/model/calibration')
    def calibration_evidence():
        service = getattr(app.state, 'service', None)
        if service is None:
            raise HTTPException(503, 'Model is not ready; calibration evidence is unavailable.')
        try:
            return get_calibration_evidence(getattr(service, 'calibration', None), service.version)
        except ValueError as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get('/health/database')
    def database_health():
        result = check_database_connection()
        if result['status'] != 'connected':
            raise HTTPException(503, 'Database connection is not available.')
        return result

    @app.get('/health')
    def health():
        service = getattr(app.state, 'service', None)
        return dict(
            status='ready' if service else 'unavailable',
            model_version=service.version if service else None,
            capabilities={
                'xai': ['integrated_gradients', 'metadata_shapley'] if service and not getattr(service, 'requires_clinical', False) and xai_available() else [],
                'grad_cam': 'not_implemented',
                'shap': 'not_implemented',
                'attention': 'not_implemented',
            },
        )

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

    @app.put('/api/v1/assessments/{assessment_id}')
    async def update_assessment(assessment_id: UUID, assessment: DoctorAssessmentUpdate):
        try:
            updated = await run_in_threadpool(update_doctor_assessment, str(assessment_id), assessment.model_dump())
            if not updated:
                raise HTTPException(404, 'Report not found.')
            return updated
        except DatabaseUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.delete('/api/v1/assessments/{assessment_id}')
    async def remove_assessment(assessment_id: UUID):
        try:
            deleted = await run_in_threadpool(delete_doctor_assessment, str(assessment_id))
            if not deleted:
                raise HTTPException(404, 'Report not found.')
            return {'deleted': True}
        except DatabaseUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.post('/api/v1/reports/pdf')
    async def export_report_pdf(payload: ReportPdfRequest):
        safe_name = re.sub(r'[^A-Za-z0-9._-]+', '_', payload.filename).strip('._') or 'skin-lesion-report.pdf'
        if not safe_name.lower().endswith('.pdf'):
            safe_name += '.pdf'
        try:
            pdf_bytes = await run_in_threadpool(_render_html_to_pdf, payload.html)
        except Exception as exc:
            logger.warning('PDF generation unavailable: %s', exc)
            raise HTTPException(503, str(exc)) from exc
        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{safe_name}"'},
        )

    @app.post('/api/v1/prescriptions', status_code=201)
    async def create_prescription_record(prescription: PrescriptionCreate):
        try:
            return await run_in_threadpool(create_prescription, prescription.model_dump())
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        except DatabaseUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get('/api/v1/prescriptions')
    async def get_prescriptions(limit: int = Query(default=100, ge=1, le=200)):
        try:
            return await run_in_threadpool(list_prescriptions, limit)
        except DatabaseUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get('/api/v1/medicines/suggest')
    async def medicine_suggestions(q: str = Query(min_length=3, max_length=80)):
        try:
            return await run_in_threadpool(suggest_medicines, q)
        except MedicineCatalogUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc

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
                    result = await run_in_threadpool(service.predict, decoded, age, sex, site, clinical_image)
                else:
                    result = await run_in_threadpool(service.predict, decoded, age, sex, site)
                # This unauthenticated API is restricted to local research use.
                # Persistence must be explicitly enabled after the migration is applied.
                if os.getenv('ANALYSIS_PERSISTENCE_ENABLED', '').lower() == 'true':
                    snapshot = {**result, 'persistence': 'saved'}
                    try:
                        await run_in_threadpool(save_analysis_snapshot, snapshot)
                        return {**snapshot, 'assistant_access_token': await run_in_threadpool(case_sessions.register,snapshot)}
                    except DatabaseUnavailable:
                        logger.warning('Analysis was not saved')
                        result = {**result, 'persistence': 'not_saved', 'persistence_reason': 'database_unavailable'}
                return {**result, 'assistant_access_token': await run_in_threadpool(case_sessions.register,result)}
            except AssistantStorageUnavailable:
                return {**result,'assistant_access_token':None,'assistant_status':'storage_unavailable'}
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

    @app.post('/api/v1/chat/query')
    async def chat_query(query: ChatQuery, x_case_token: str = Header(default='', max_length=128)):
        try:
            context = await run_in_threadpool(case_sessions.get,str(query.analysis_id),x_case_token)
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        conversation = await run_in_threadpool(history.conversation, str(query.analysis_id))
        citations = []
        route = route_question(query.question,context,conversation)
        context = {**context, 'question_intent':route['intent'], 'response_language':route['language'], 'requested_class':route.get('class_label',context['leading_class'])}
        if route.get('response'):
            answer = route['response']
        elif route['intent'] == 'reason' and context.get('xai') is None:
            answer = reason_answer(context,route['language'])
        elif route['intent'] == 'parameters':
            answer = parameter_answer(context,route['language'])
        elif route['intent']=='prediction':
            answer = prediction_answer(context,route['language'],route['all_scores'],route['class_label'] if route.get('explicit_class') else None)
        elif route['intent'] in ('uncertainty','calibration','agreement','limitations'):
            answer = case_fact_answer(route['intent'],context,route['language'])
        else:
            stage='retrieval'
            try:
                if provider == 'gemini' and (online_url or knowledge_path.exists() or os.getenv('KNOWLEDGE_DATABASE_URL')):
                    store = PostgresKnowledgeStore(online_url,schema='assistant') if online_url else (PostgresKnowledgeStore(os.environ['KNOWLEDGE_DATABASE_URL']) if os.getenv('KNOWLEDGE_DATABASE_URL') else LocalKnowledgeStore(knowledge_path))
                    retriever = HybridRetriever(store, GeminiEmbeddings())
                    retrieval_question = route['retrieval_question'] if route['intent'] in ('disease','reason') else build_retrieval_query(query.question,conversation)
                    citations = await run_in_threadpool(retriever.search, retrieval_question, 3, context['model_version'], route['intent'], route.get('class_label'))
                    context = {**context, 'knowledge_sources': citations}
                stage='generation'
                answer = await run_in_threadpool(generator.answer, query.question, context, conversation)
            except (GeminiUnavailable, ValueError) as exc:
                # Log only a fixed stage and our sanitized exception message, never case text or prompts.
                status_match=re.search(r'HTTP (\d{3})',str(exc))
                logger.warning('Assistant %s failure (%s)',stage,'HTTP '+status_match.group(1) if status_match else type(exc).__name__)
                overview=await run_in_threadpool(class_overviews.get,route['class_label'],route['language']) if class_overviews and eligible_overview(query.question,route) else None
                if overview:
                    answer,citations=overview
                else:
                    message=('উত্তর তৈরির service সাময়িকভাবে পাওয়া যাচ্ছে না। আবার চেষ্টা করো। Prediction, uncertainty ও parameters এখনো দেখা যাবে।' if route['language']=='bn' else 'The answer service is temporarily unavailable. Please retry. Prediction, uncertainty and case parameters are still available.')
                    raise HTTPException(503,message,headers={'Retry-After':'3'}) from exc
        if answer.get('status')=='unavailable' and class_overviews and eligible_overview(query.question,route):
            overview=await run_in_threadpool(class_overviews.get,route['class_label'],route['language'])
            if overview:answer,citations=overview
        citations = used_citations(answer,citations)
        response = {**answer, 'analysis_id': str(query.analysis_id), 'provider': provider,
                'citations': citations, 'model_version': context['model_version'],
                'input_hash': context['input_hash']}
        response['message_id'] = await run_in_threadpool(history.add, str(query.analysis_id), query.question, response)
        return response

    @app.get('/api/v1/chat/case/{analysis_id}')
    def restore_chat_case(analysis_id: UUID, response: Response, x_case_token: str = Header(default='', max_length=128)):
        try:
            context=case_sessions.get(str(analysis_id),x_case_token)
        except PermissionError as exc:
            raise HTTPException(403,str(exc)) from exc
        response.headers['Cache-Control']='no-store'
        return {**context,'classes':[row['label'] for row in context['scores']], 'elapsed_ms':0,
                'persistence':context.get('persistence','not_saved')}

    @app.get('/api/v1/chat/history/{analysis_id}')
    async def chat_history(analysis_id: UUID, response: Response, x_case_token: str = Header(default='', max_length=128)):
        try:
            await run_in_threadpool(case_sessions.get,str(analysis_id),x_case_token)
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        response.headers['Cache-Control']='no-store'
        return await run_in_threadpool(history.list, str(analysis_id))

    @app.post('/api/v1/chat/feedback')
    async def chat_feedback(feedback: ChatFeedback, x_case_token: str = Header(default='', max_length=128)):
        try:
            await run_in_threadpool(case_sessions.get,str(feedback.analysis_id),x_case_token)
            await run_in_threadpool(history.rate, str(feedback.analysis_id), str(feedback.message_id), feedback.rating)
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
        return {'status': 'saved'}

    @app.post('/api/v1/explanations', status_code=202)
    async def explain(bg: BackgroundTasks,
                      image: UploadFile = File(...), age: float = Form(...), sex: str = Form(...),
                      site: str = Form("unknown"), target_class: str = Form(None), fold: int = Form(None),
                      method: str = Form("integrated_gradients"), n_steps: int = Form(5),
                      baseline: str = Form("blur"), include_metadata: bool = Form(True),
                      analysis_id: UUID | None = Form(None), x_case_token: str = Header(default='')):
        _cleanup_jobs()
        if analysis_id is not None:
            try:
                await run_in_threadpool(case_sessions.get,str(analysis_id),x_case_token)
            except PermissionError as exc:
                raise HTTPException(403, str(exc)) from exc
        try:
            encode_metadata(age, sex, site)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if method != 'integrated_gradients':
            raise HTTPException(422, 'Unknown explanation method.')
        if target_class is not None and target_class not in CLASSES:
            raise HTTPException(422, 'Unknown target class.')
        if fold is not None and not 0 <= fold <= 4:
            raise HTTPException(422, 'Fold must be between 0 and 4.')
        if not 4 <= n_steps <= 50:
            raise HTTPException(422, 'n_steps must be between 4 and 50.')
        if baseline not in ('blur', 'zero'):
            raise HTTPException(422, 'Baseline must be blur or zero.')
        service = getattr(app.state, 'service', None)
        if service is None:
            raise HTTPException(503, 'Model unavailable. Complete the backend model setup.')
        if getattr(service, 'requires_clinical', False):
            raise HTTPException(422, 'Explanation support for this DermFM configuration is not yet available.')

        try:
            contents = await image.read(MAX_BYTES+1)
            try:
                decoded = decode_image(contents)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
        finally:
            await image.close()

        key = _xai_cache_key(contents, age, sex, site, target_class, fold, n_steps, baseline, include_metadata)
        job_id = str(uuid.uuid4())

        if key in cache:
            cached_result = cache[key]
            if analysis_id is not None:
                try:
                    await run_in_threadpool(case_sessions.attach_explanation,str(analysis_id),x_case_token,cached_result)
                except ValueError as exc:
                    raise HTTPException(409, 'Explanation does not match this analysis.') from exc
            jobs[job_id] = {
                "status": "done",
                "stage": "done",
                "result": cached_result,
                "created": time.time(),
            }
            return {"job_id": job_id, "status": "done"}

        jobs[job_id] = {
            "status": "queued",
            "stage": "queued",
            "created": time.time(),
        }
        bg.add_task(
            _xai_worker,
            job_id, service, decoded, age, sex, site,
            target_class, fold, n_steps, baseline, include_metadata, key,
            case_sessions, str(analysis_id) if analysis_id is not None else None, x_case_token,
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

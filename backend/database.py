"""Small PostgreSQL connectivity helper for the development API."""
from __future__ import annotations

import logging
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load local secrets for direct PowerShell runs; Docker can also provide env vars.
load_dotenv(Path(__file__).with_name(".env"), override=False)


class DatabaseUnavailable(RuntimeError):
    pass


def _database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise DatabaseUnavailable("Database is not configured")
    return value


def check_database_connection() -> dict[str, str]:
    """Run a read-only connectivity check without exposing connection details."""
    try:
        database_url = _database_url()
    except DatabaseUnavailable:
        return {"status": "not_configured"}

    try:
        with psycopg.connect(database_url, connect_timeout=5) as connection:
            database_name = connection.execute("SELECT current_database()").fetchone()[0]
        return {"status": "connected", "database": database_name}
    except Exception as exc:
        # Never log the exception message: drivers may include connection details.
        logger.warning("Database connectivity check failed (%s)", type(exc).__name__)
        return {"status": "unavailable"}


def create_doctor_assessment(payload: dict) -> dict:
    query = """
        INSERT INTO public.doctor_assessments (
            patient_id, patient_name, analysis_id, model_version, leading_class, model_scores, patient_metadata,
            image_snapshot, uncertainty, ensemble, input_policy, tta, limitations,
            decision, confidence, suspected_diagnosis, differential_diagnoses,
            clinical_note, next_action
        ) VALUES (
            %(patient_id)s, %(patient_name)s, %(analysis_id)s, %(model_version)s, %(leading_class)s, %(model_scores)s,
            %(patient_metadata)s, %(image_snapshot)s, %(uncertainty)s, %(ensemble)s,
            %(input_policy)s, %(tta)s, %(limitations)s, %(decision)s, %(confidence)s, %(suspected_diagnosis)s,
            %(differential_diagnoses)s, %(clinical_note)s, %(next_action)s
        )
        RETURNING id, patient_id, patient_name, analysis_id, model_version, leading_class, model_scores,
                  patient_metadata, image_snapshot, uncertainty, ensemble, input_policy, tta,
                  limitations, decision, confidence,
                  suspected_diagnosis, differential_diagnoses, clinical_note,
                  next_action, reviewer_user_id, reviewer_name, created_at
    """
    parameters = {
        **payload,
        "model_scores": Jsonb(payload["model_scores"]),
        "patient_metadata": Jsonb(payload["patient_metadata"]),
        "uncertainty": Jsonb(payload["uncertainty"]),
        "ensemble": Jsonb(payload["ensemble"]),
    }
    try:
        with psycopg.connect(_database_url(), connect_timeout=8, row_factory=dict_row) as connection:
            return dict(connection.execute(query, parameters).fetchone())
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        logger.exception("Could not create doctor assessment (%s)", type(exc).__name__)
        raise DatabaseUnavailable("Assessment storage is unavailable") from exc


def list_doctor_assessments(limit: int = 50) -> list[dict]:
    query = """
        SELECT id, patient_id, patient_name, analysis_id, model_version, leading_class, model_scores,
               patient_metadata, image_snapshot, uncertainty, ensemble, input_policy, tta,
               limitations, decision, confidence,
               suspected_diagnosis, differential_diagnoses, clinical_note,
               next_action, reviewer_user_id, reviewer_name, created_at
        FROM public.doctor_assessments
        ORDER BY created_at DESC
        LIMIT %s
    """
    try:
        with psycopg.connect(_database_url(), connect_timeout=8, row_factory=dict_row) as connection:
            return [dict(row) for row in connection.execute(query, (limit,)).fetchall()]
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        logger.exception("Could not list doctor assessments (%s)", type(exc).__name__)
        raise DatabaseUnavailable("Assessment storage is unavailable") from exc


def create_prescription(payload: dict) -> dict:
    query = """
        INSERT INTO public.prescriptions (
            assessment_id, patient_id, patient_name, analysis_id, model_version, leading_class,
            patient_metadata, symptoms, allergy_status, allergy_details, medications, follow_up
        ) VALUES (
            %(assessment_id)s, %(patient_id)s, %(patient_name)s, %(analysis_id)s, %(model_version)s,
            %(leading_class)s, %(patient_metadata)s, %(symptoms)s, %(allergy_status)s,
            %(allergy_details)s, %(medications)s, %(follow_up)s
        )
        RETURNING id, assessment_id, patient_id, patient_name, analysis_id, model_version,
                  leading_class, patient_metadata, symptoms, allergy_status,
                  allergy_details, medications, follow_up, prescriber_user_id,
                  prescriber_name, created_at
    """
    parameters = {
        **payload,
        "patient_metadata": Jsonb(payload["patient_metadata"]),
        "medications": Jsonb(payload["medications"]),
    }
    try:
        with psycopg.connect(_database_url(), connect_timeout=8, row_factory=dict_row) as connection:
            return dict(connection.execute(query, parameters).fetchone())
    except DatabaseUnavailable:
        raise
    except psycopg.errors.UniqueViolation as exc:
        raise ValueError("A prescription already exists for this analysis") from exc
    except Exception as exc:
        logger.exception("Could not create prescription (%s)", type(exc).__name__)
        raise DatabaseUnavailable("Prescription storage is unavailable") from exc


def list_prescriptions(limit: int = 100) -> list[dict]:
    query = """
        SELECT id, assessment_id, patient_id, patient_name, analysis_id, model_version,
               leading_class, patient_metadata, symptoms, allergy_status,
               allergy_details, medications, follow_up, prescriber_user_id,
               prescriber_name, created_at
        FROM public.prescriptions
        ORDER BY created_at DESC
        LIMIT %s
    """
    try:
        with psycopg.connect(_database_url(), connect_timeout=8, row_factory=dict_row) as connection:
            return [dict(row) for row in connection.execute(query, (limit,)).fetchall()]
    except DatabaseUnavailable:
        raise
    except Exception as exc:
        logger.exception("Could not list prescriptions (%s)", type(exc).__name__)
        raise DatabaseUnavailable("Prescription storage is unavailable") from exc

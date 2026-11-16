"""Small PostgreSQL connectivity helper for the development API."""
from __future__ import annotations

import logging
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load local secrets for direct PowerShell runs; Docker can also provide env vars.
load_dotenv(Path(__file__).with_name(".env"), override=False)


def check_database_connection() -> dict[str, str]:
    """Run a read-only connectivity check without exposing connection details."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {"status": "not_configured"}

    try:
        with psycopg.connect(database_url, connect_timeout=5) as connection:
            database_name = connection.execute("SELECT current_database()").fetchone()[0]
        return {"status": "connected", "database": database_name}
    except Exception as exc:
        # Never log the exception message: drivers may include connection details.
        logger.warning("Database connectivity check failed (%s)", type(exc).__name__)
        return {"status": "unavailable"}

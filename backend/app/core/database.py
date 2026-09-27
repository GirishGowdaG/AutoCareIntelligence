"""Strict Read-Only Database Session Management for AutoCare Intelligence.

Guarantees that all connections to PostgreSQL operate in read-only mode,
preventing any data modification or schema alterations.
"""

from contextlib import contextmanager
import logging
from typing import Generator, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor

from backend.app.core.config import get_app_settings

logger = logging.getLogger(__name__)


@contextmanager
def get_db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """Context manager yielding a strictly read-only PostgreSQL connection."""
    settings = get_app_settings()
    conn = psycopg2.connect(**settings.pg_config)
    try:
        # Enforce PostgreSQL transaction-level read-only mode
        conn.set_session(readonly=True, autocommit=True)
        yield conn
    finally:
        conn.close()


def execute_read_query(query: str, params: Any = None) -> list:
    """Execute a SELECT query against PostgreSQL in read-only mode and return list of dicts."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [dict(row) for row in cur.fetchall()]


def execute_read_scalar(query: str, params: Any = None) -> Any:
    """Execute a query returning a single scalar value."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return row[0] if row else None

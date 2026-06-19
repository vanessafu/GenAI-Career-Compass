"""Shared psycopg2 connection pool for all backend components."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator, Optional

import psycopg2
from pgvector.psycopg2 import register_vector
from psycopg2.pool import SimpleConnectionPool

from backend.app.core.config import DATABASE_URL

logger = logging.getLogger("CareerCompass.Database")

db_pool: Optional[SimpleConnectionPool] = None

try:
    db_pool = SimpleConnectionPool(
        minconn=2, maxconn=15, dsn=DATABASE_URL, keepalives=1
    )
    logger.info("Initialized SimpleConnectionPool (Supabase pooler mode).")
except Exception as exc:  # noqa: BLE001
    logger.error("Failed to create database connection pool: %s", exc)


@contextmanager
def get_db_connection() -> Iterator[psycopg2.extensions.connection]:
    """Yield a pooled psycopg2 connection with the pgvector adapter registered."""
    if db_pool is None:
        raise RuntimeError("Database connection pool is uninitialized or failed to start.")
    conn = db_pool.getconn()
    try:
        register_vector(conn)
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        db_pool.putconn(conn)

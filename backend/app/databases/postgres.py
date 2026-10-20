"""PostgreSQL connection lifecycle helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from app.config import get_settings


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    """Yield one transaction-scoped PostgreSQL connection."""

    settings = get_settings()
    connection = psycopg.connect(
        settings.database_url,
        connect_timeout=settings.postgres_connect_timeout,
        row_factory=dict_row,
    )
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

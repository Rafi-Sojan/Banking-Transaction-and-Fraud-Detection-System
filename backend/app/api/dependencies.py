"""Reusable FastAPI dependencies."""

from collections.abc import Iterator

import psycopg

from app.databases.postgres import get_connection


def get_db() -> Iterator[psycopg.Connection]:
    with get_connection() as connection:
        yield connection

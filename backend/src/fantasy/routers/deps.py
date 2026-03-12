from __future__ import annotations

from collections.abc import Generator

import duckdb

from fantasy.db.connection import get_read_connection, get_write_connection


def get_write_db_conn() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    conn = get_write_connection()
    try:
        yield conn
    finally:
        conn.close()


def get_read_db_conn() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    conn = get_read_connection()
    try:
        yield conn
    finally:
        conn.close()

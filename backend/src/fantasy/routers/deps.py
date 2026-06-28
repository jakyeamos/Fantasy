from __future__ import annotations

from collections.abc import Generator
from threading import Lock

import duckdb

from fantasy.db.connection import (
    close_connection,
    get_read_connection,
    get_write_connection,
)

_WRITE_DEPENDENCY_LOCK = Lock()


def get_write_db_conn() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    with _WRITE_DEPENDENCY_LOCK:
        conn = get_write_connection()
        try:
            yield conn
        finally:
            close_connection(conn)


def get_read_db_conn() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    conn = get_read_connection()
    try:
        yield conn
    finally:
        close_connection(conn)

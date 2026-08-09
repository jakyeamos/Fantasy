from __future__ import annotations

from collections.abc import Generator
from threading import Lock

import duckdb

from fantasy.db.connection import (
    close_connection,
    get_read_connection,
    get_write_connection,
)

# DuckDB is embedded and this app opens a short-lived connection per request.
# Serializing the full dependency lifetime prevents a read request from racing
# the teardown of a write request and attempting to attach a second file handle.
_DB_DEPENDENCY_LOCK = Lock()


def get_write_db_conn() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    with _DB_DEPENDENCY_LOCK:
        conn = get_write_connection()
        try:
            yield conn
        finally:
            close_connection(conn)


def get_read_db_conn() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    with _DB_DEPENDENCY_LOCK:
        conn = get_read_connection()
        try:
            yield conn
        finally:
            close_connection(conn)

from pathlib import Path
from threading import RLock

import duckdb

from fantasy.config import get_settings

_CONNECTION_LOCK = RLock()
_SHARED_CONNECTIONS: dict[str, duckdb.DuckDBPyConnection] = {}
_SHARED_CONNECTION_IDS: set[int] = set()


def _resolve_path(path_value: str) -> str:
    if path_value == ":memory:":
        return path_value

    path = Path(path_value)
    if not path.is_absolute():
        repo_root = Path(__file__).resolve().parents[4]
        path = (repo_root / path).resolve()

    return str(path)


def get_write_connection() -> duckdb.DuckDBPyConnection:
    """Open a write-capable connection to DuckDB."""

    settings = get_settings()
    db_path = _resolve_path(settings.db_path)
    if db_path == ":memory:":
        return duckdb.connect(db_path)
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return _connect_shared_database(db_path)


def _connect_shared_database(db_path: str) -> duckdb.DuckDBPyConnection:
    with _CONNECTION_LOCK:
        existing = _SHARED_CONNECTIONS.get(db_path)
        if existing is not None:
            return existing
        conn = duckdb.connect(db_path)
        _SHARED_CONNECTIONS[db_path] = conn
        _SHARED_CONNECTION_IDS.add(id(conn))
        return conn


def close_connection(conn: duckdb.DuckDBPyConnection) -> None:
    if id(conn) in _SHARED_CONNECTION_IDS:
        return
    conn.close()


def get_read_connection() -> duckdb.DuckDBPyConnection:
    """Open a read-only connection when possible."""

    settings = get_settings()
    db_path = _resolve_path(settings.db_path)

    if db_path == ":memory:":
        return duckdb.connect(db_path)

    return _connect_shared_database(db_path)

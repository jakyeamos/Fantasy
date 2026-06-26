from pathlib import Path

import duckdb

from fantasy.config import get_settings


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
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(db_path)


def close_connection(conn: duckdb.DuckDBPyConnection) -> None:
    conn.close()


def get_read_connection() -> duckdb.DuckDBPyConnection:
    """Open a read-only connection when possible."""

    settings = get_settings()
    db_path = _resolve_path(settings.db_path)

    return duckdb.connect(db_path, read_only=db_path != ":memory:")

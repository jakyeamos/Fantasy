from __future__ import annotations

from fantasy.db import connection


def test_file_connections_reuse_one_shared_handle(monkeypatch):
    calls: list[tuple[str, bool | None]] = []
    sentinel = object()

    def _fake_connect(path: str, read_only: bool | None = None):
        calls.append((path, read_only))
        return sentinel

    monkeypatch.setattr(connection.duckdb, "connect", _fake_connect)
    connection._SHARED_CONNECTIONS.clear()
    connection._SHARED_CONNECTION_IDS.clear()

    assert connection._connect_shared_database("/tmp/fantasy.duckdb") is sentinel
    assert connection._connect_shared_database("/tmp/fantasy.duckdb") is sentinel
    assert calls == [("/tmp/fantasy.duckdb", None)]


def test_close_connection_keeps_shared_handles_open(monkeypatch):
    class _FakeConnection:
        def __init__(self):
            self.closed = False

        def close(self) -> None:
            self.closed = True

    shared = _FakeConnection()
    regular = _FakeConnection()
    monkeypatch.setattr(connection, "_SHARED_CONNECTION_IDS", {id(shared)})

    connection.close_connection(shared)  # type: ignore[arg-type]
    connection.close_connection(regular)  # type: ignore[arg-type]

    assert shared.closed is False
    assert regular.closed is True

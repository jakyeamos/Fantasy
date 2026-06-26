from __future__ import annotations

from fantasy.db import connection


def test_file_connections_open_independent_handles(monkeypatch):
    calls: list[tuple[str, bool | None]] = []
    sentinels = [object(), object()]

    def _fake_connect(path: str, read_only: bool | None = None):
        calls.append((path, read_only))
        return sentinels[len(calls) - 1]

    monkeypatch.setattr(connection.duckdb, "connect", _fake_connect)

    assert connection.get_write_connection() is sentinels[0]
    assert connection.get_write_connection() is sentinels[1]
    assert calls == [
        (connection.get_settings().db_path, None),
        (connection.get_settings().db_path, None),
    ]


def test_read_connection_uses_read_only_file_handle(monkeypatch):
    calls: list[tuple[str, bool | None]] = []
    sentinel = object()

    def _fake_connect(path: str, read_only: bool | None = None):
        calls.append((path, read_only))
        return sentinel

    monkeypatch.setattr(connection.duckdb, "connect", _fake_connect)

    assert connection.get_read_connection() is sentinel
    assert calls == [(connection.get_settings().db_path, True)]


def test_close_connection_closes_handle():
    class _FakeConnection:
        def __init__(self):
            self.closed = False

        def close(self) -> None:
            self.closed = True

    regular = _FakeConnection()

    connection.close_connection(regular)  # type: ignore[arg-type]

    assert regular.closed is True

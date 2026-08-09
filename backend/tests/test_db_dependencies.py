from __future__ import annotations

from threading import Event, Thread

from fantasy.routers import deps


class _FakeConnection:
    def close(self) -> None:
        pass


def test_read_dependency_waits_for_write_connection_teardown(monkeypatch) -> None:
    write_open = Event()
    release_write = Event()
    read_opened = Event()

    monkeypatch.setattr(deps, "get_write_connection", _FakeConnection)

    def _open_read() -> _FakeConnection:
        read_opened.set()
        return _FakeConnection()

    monkeypatch.setattr(deps, "get_read_connection", _open_read)

    def _hold_write() -> None:
        dependency = deps.get_write_db_conn()
        next(dependency)
        write_open.set()
        release_write.wait(timeout=2)
        dependency.close()

    def _read() -> None:
        dependency = deps.get_read_db_conn()
        next(dependency)
        dependency.close()

    writer = Thread(target=_hold_write)
    reader = Thread(target=_read)
    writer.start()
    assert write_open.wait(timeout=1)
    reader.start()

    assert not read_opened.wait(timeout=0.05)
    release_write.set()
    writer.join(timeout=1)
    reader.join(timeout=1)

    assert not writer.is_alive()
    assert not reader.is_alive()
    assert read_opened.is_set()

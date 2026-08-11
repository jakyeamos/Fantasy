from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

import fantasy.main as main
from httpx import ASGITransport, AsyncClient


async def test_background_refresh_runs_outside_the_event_loop(monkeypatch):
    connection = object()
    refresh_started = threading.Event()
    release_refresh = threading.Event()
    refresh_thread_ids: list[int] = []
    closed_connections: list[object] = []

    async def fake_refresh(conn, _settings):
        assert conn is connection
        refresh_thread_ids.append(threading.get_ident())
        refresh_started.set()
        assert release_refresh.wait(timeout=1.0)

    async def wait_for_refresh_start() -> None:
        while not refresh_started.is_set():
            await asyncio.sleep(0)

    monkeypatch.setattr(main, "get_write_connection", lambda: connection)
    monkeypatch.setattr(main, "maybe_run_dev_refresh", fake_refresh)
    monkeypatch.setattr(main, "close_connection", closed_connections.append)

    event_loop_thread_id = threading.get_ident()
    task = asyncio.create_task(main._background_dev_refresh(object()))
    await asyncio.wait_for(wait_for_refresh_start(), timeout=0.5)

    assert refresh_thread_ids != [event_loop_thread_id]
    assert not task.done()

    release_refresh.set()
    await asyncio.wait_for(task, timeout=0.5)
    assert closed_connections == [connection]


async def test_healthz_responds_while_dev_refresh_worker_is_busy(monkeypatch):
    refresh_started = threading.Event()
    release_refresh = threading.Event()

    def blocking_refresh(_settings):
        refresh_started.set()
        assert release_refresh.wait(timeout=1.0)

    async def wait_for_refresh_start() -> None:
        while not refresh_started.is_set():
            await asyncio.sleep(0)

    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: SimpleNamespace(DEV_AUTO_REFRESH=True),
    )
    monkeypatch.setattr(main, "get_write_connection", object)
    monkeypatch.setattr(main, "close_connection", lambda _conn: None)
    monkeypatch.setattr(main, "ensure_runtime_schema", lambda _conn: None)
    monkeypatch.setattr(main, "load_adp_baseline", lambda _conn: 0)
    monkeypatch.setattr(main, "_run_dev_refresh_in_worker", blocking_refresh)

    app = main.create_app()
    try:
        async with app.router.lifespan_context(app):
            await asyncio.wait_for(wait_for_refresh_start(), timeout=0.5)
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await asyncio.wait_for(client.get("/healthz"), timeout=0.5)

            assert response.status_code == 200
            assert response.json() == {
                "status": "ok",
                "service": "fantasy-backend",
            }
            release_refresh.set()
    finally:
        release_refresh.set()

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_dev_launcher_runs_migrations_before_backend(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    backend_bin = repo / "backend" / ".venv" / "bin"
    frontend = repo / "frontend"
    command_bin = tmp_path / "bin"
    log_path = tmp_path / "launcher.log"

    backend_bin.mkdir(parents=True)
    frontend.mkdir(parents=True)
    command_bin.mkdir()
    shutil.copy2(REPO_ROOT / "dev.sh", repo / "dev.sh")

    logger = f'printf "%s\\n" "$*" >> "{log_path}"\n'
    _write_executable(
        backend_bin / "alembic",
        f"#!/usr/bin/env bash\n{logger!s}",
    )
    _write_executable(
        backend_bin / "uvicorn",
        f"#!/usr/bin/env bash\n{logger!s}",
    )
    _write_executable(
        command_bin / "pnpm",
        f"#!/usr/bin/env bash\n{logger!s}",
    )

    env = os.environ.copy()
    env["PATH"] = f"{command_bin}:{env['PATH']}"
    result = subprocess.run(
        ["bash", str(repo / "dev.sh")],
        check=False,
        env=env,
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    commands = log_path.read_text().splitlines()
    assert commands[0] == "upgrade heads"
    assert "fantasy.main:app --reload" in commands
    assert "dev" in commands
    assert commands.index("upgrade heads") < commands.index("fantasy.main:app --reload")

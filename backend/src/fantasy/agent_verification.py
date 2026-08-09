"""One machine-readable readiness boundary for fantasy-agent work."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import duckdb

from fantasy.capabilities import build_capability_manifest
from fantasy.config import REPO_ROOT, get_settings


@dataclass(frozen=True)
class CommandSpec:
    name: str
    command: tuple[str, ...]
    cwd: Path


def _command_specs(repo_root: Path) -> list[CommandSpec]:
    backend = repo_root / "backend"
    frontend = repo_root / "frontend"
    python = sys.executable
    alembic = str(backend / ".venv" / "bin" / "alembic")
    return [
        CommandSpec("migration_head", (alembic, "current"), backend),
        CommandSpec("backend_tests", (python, "-m", "pytest", "-q"), backend),
        CommandSpec("frontend_format", ("pnpm", "format"), frontend),
        CommandSpec("frontend_typecheck", ("pnpm", "typecheck"), frontend),
        CommandSpec("frontend_dead_code", ("pnpm", "audit:dead-code"), frontend),
        CommandSpec("frontend_build", ("pnpm", "build"), frontend),
        CommandSpec("git_diff_check", ("git", "diff", "--check"), repo_root),
    ]


def _tail(value: str, limit: int = 2000) -> str:
    stripped = value.strip()
    return stripped[-limit:] if stripped else "passed"


def run_command(spec: CommandSpec) -> dict[str, Any]:
    executable = spec.command[0]
    resolved = (
        str(Path(executable))
        if Path(executable).is_absolute() and Path(executable).exists()
        else shutil.which(executable)
    )
    if resolved is None:
        return {
            "name": spec.name,
            "state": "unavailable",
            "command": list(spec.command),
            "exit_code": None,
            "detail": f"Required executable is unavailable: {executable}",
        }
    result = subprocess.run(
        spec.command,
        cwd=spec.cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    output = "\n".join(part for part in [result.stdout, result.stderr] if part)
    state = "passed" if result.returncode == 0 else "failed"
    detail = _tail(output)
    if spec.name == "migration_head" and state == "passed" and "(head)" not in output:
        state = "failed"
        detail = f"Database is not at the migration head.\n{detail}"
    return {
        "name": spec.name,
        "state": state,
        "command": list(spec.command),
        "resolved_executable": resolved,
        "exit_code": result.returncode,
        "detail": detail,
    }


def _load_capabilities(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        return {
            "schema_version": "fantasy-agent-capabilities/1.0",
            "capabilities": {
                "local_database": {
                    "provider": "native",
                    "runtime_state": "unavailable",
                    "database_path": str(db_path),
                }
            },
        }
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        return build_capability_manifest(conn)
    finally:
        conn.close()


def _capability_checks(
    manifest: dict[str, Any],
    *,
    command_states: dict[str, str],
) -> list[dict[str, Any]]:
    state_map = {
        "available": "passed",
        "degraded": "degraded",
        "missing": "degraded",
        "unavailable": "unavailable",
        "unsupported": "unavailable",
        "verification_required": "unavailable",
        "blocked": "failed",
    }
    checks = []
    for name, evidence in sorted(manifest.get("capabilities", {}).items()):
        runtime_state = str(evidence.get("runtime_state", "unavailable"))
        check_state = state_map.get(runtime_state, "unavailable")
        reported_state = runtime_state
        if (
            name == "golden_agent_evaluations"
            and runtime_state == "verification_required"
            and command_states.get("backend_tests") == "passed"
        ):
            check_state = "passed"
            reported_state = "behavior_verified"
        checks.append(
            {
                "name": f"capability:{name}",
                "state": check_state,
                "runtime_state": reported_state,
                "declared_runtime_state": runtime_state,
                "provider": evidence.get("provider", "unknown"),
                "detail": evidence,
            }
        )
    return checks


def run_agent_verification(
    *,
    repo_root: Path = REPO_ROOT,
    command_runner: Callable[[CommandSpec], dict[str, Any]] = run_command,
    capability_loader: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    checks = [command_runner(spec) for spec in _command_specs(repo_root)]
    loader = capability_loader or (
        lambda: _load_capabilities(Path(get_settings().db_path))
    )
    command_states = {check["name"]: check["state"] for check in checks}
    checks.extend(_capability_checks(loader(), command_states=command_states))
    counts = Counter(check["state"] for check in checks)
    precedence = ("failed", "degraded", "unavailable", "passed")
    overall_state = next(state for state in precedence if counts[state])
    return {
        "schema_version": "fantasy-agent-verification/1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall_state": overall_state,
        "summary": {state: counts[state] for state in ("passed", "degraded", "unavailable", "failed")},
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the complete fantasy-agent readiness boundary."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON (default output)")
    parser.parse_args(argv)
    report = run_agent_verification()
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return {"passed": 0, "failed": 1, "degraded": 2, "unavailable": 3}[
        report["overall_state"]
    ]


if __name__ == "__main__":
    raise SystemExit(main())

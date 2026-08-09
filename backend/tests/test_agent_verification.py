from __future__ import annotations

from fantasy.agent_verification import CommandSpec, run_agent_verification


def _manifest(*states: str) -> dict:
    return {
        "schema_version": "fantasy-agent-capabilities/1.0",
        "capabilities": {
            f"capability_{index}": {
                "provider": "native",
                "runtime_state": state,
            }
            for index, state in enumerate(states)
        },
    }


def test_verification_report_preserves_degraded_and_unavailable_states(tmp_path):
    seen: list[str] = []

    def runner(spec: CommandSpec) -> dict:
        seen.append(spec.name)
        return {
            "name": spec.name,
            "state": "passed",
            "command": list(spec.command),
            "exit_code": 0,
            "detail": "passed",
        }

    report = run_agent_verification(
        repo_root=tmp_path,
        command_runner=runner,
        capability_loader=lambda: _manifest("available", "degraded", "unavailable"),
    )

    assert report["schema_version"] == "fantasy-agent-verification/1.0"
    assert report["overall_state"] == "degraded"
    assert seen == [
        "migration_head",
        "backend_tests",
        "frontend_format",
        "frontend_typecheck",
        "frontend_dead_code",
        "frontend_build",
        "git_diff_check",
    ]
    states = {check["name"]: check["state"] for check in report["checks"]}
    assert states["capability:capability_0"] == "passed"
    assert states["capability:capability_1"] == "degraded"
    assert states["capability:capability_2"] == "unavailable"


def test_verification_report_marks_command_failure_without_losing_other_states(tmp_path):
    def runner(spec: CommandSpec) -> dict:
        state = "failed" if spec.name == "frontend_build" else "passed"
        return {
            "name": spec.name,
            "state": state,
            "command": list(spec.command),
            "exit_code": 1 if state == "failed" else 0,
            "detail": "build failed" if state == "failed" else "passed",
        }

    report = run_agent_verification(
        repo_root=tmp_path,
        command_runner=runner,
        capability_loader=lambda: _manifest("unavailable"),
    )

    assert report["overall_state"] == "failed"
    assert report["summary"] == {
        "passed": 6,
        "degraded": 0,
        "unavailable": 1,
        "failed": 1,
    }


def test_full_backend_pass_promotes_golden_evaluation_to_behavior_verified(tmp_path):
    def runner(spec: CommandSpec) -> dict:
        return {
            "name": spec.name,
            "state": "passed",
            "command": list(spec.command),
            "exit_code": 0,
            "detail": "passed",
        }

    report = run_agent_verification(
        repo_root=tmp_path,
        command_runner=runner,
        capability_loader=lambda: {
            "capabilities": {
                "golden_agent_evaluations": {
                    "provider": "native",
                    "runtime_state": "verification_required",
                }
            }
        },
    )

    golden = next(
        check
        for check in report["checks"]
        if check["name"] == "capability:golden_agent_evaluations"
    )
    assert report["overall_state"] == "passed"
    assert golden["state"] == "passed"
    assert golden["runtime_state"] == "behavior_verified"
    assert golden["declared_runtime_state"] == "verification_required"

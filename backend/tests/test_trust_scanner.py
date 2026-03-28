from __future__ import annotations

from fantasy.ingestion.sleeper_mapper import LeagueSettings
from fantasy.trust.confidence import compute_trust_modifier
from fantasy.trust.scanner import scan_league_format


def _build_settings(**overrides) -> LeagueSettings:
    payload = {
        "league_id": "league_x",
        "name": "League X",
        "season": "2026",
        "scoring_settings": {"rec": 0.5, "bonus_rec_te": 0.5},
        "roster_positions": ["QB", "RB", "WR", "TE", "SUPER_FLEX", "BN"],
        "settings_blob": {
            "type": 2,
            "league_average_match": 0,
            "best_ball": 0,
            "salary_cap": 0,
        },
        "superflex": True,
        "tep": True,
        "ppr": 0.5,
    }
    payload.update(overrides)
    return LeagueSettings(**payload)


def test_standard_dynasty_half_ppr_superflex_tep_is_supported() -> None:
    scan = scan_league_format(_build_settings())
    rules = {entry.rule for entry in scan.entries}

    assert {"half_ppr", "superflex", "tep"} <= rules
    assert scan.needs_acknowledgment is False
    assert scan.league_unsupported is False


def test_median_wins_requires_acknowledgment() -> None:
    scan = scan_league_format(
        _build_settings(settings_blob={"type": 2, "league_average_match": 1})
    )

    median_entry = next(entry for entry in scan.entries if entry.rule == "median_wins")
    assert median_entry.support_level == "partially_supported"
    assert median_entry.distorts_recommendations is True
    assert scan.needs_acknowledgment is True


def test_best_ball_is_unsupported() -> None:
    scan = scan_league_format(
        _build_settings(settings_blob={"type": 2, "best_ball": 1})
    )

    best_ball_entry = next(entry for entry in scan.entries if entry.rule == "best_ball")
    assert best_ball_entry.support_level == "unsupported"
    assert scan.league_unsupported is True


def test_salary_cap_is_unsupported() -> None:
    scan = scan_league_format(
        _build_settings(settings_blob={"type": 2, "salary_cap": 1})
    )

    salary_cap_entry = next(entry for entry in scan.entries if entry.rule == "salary_cap")
    assert salary_cap_entry.support_level == "unsupported"


def test_idp_positions_are_unsupported() -> None:
    scan = scan_league_format(
        _build_settings(roster_positions=["QB", "RB", "WR", "TE", "LB", "BN"])
    )

    idp_entry = next(entry for entry in scan.entries if entry.rule == "idp")
    assert idp_entry.support_level == "unsupported"


def test_first_down_scoring_is_partially_supported() -> None:
    scan = scan_league_format(
        _build_settings(
            scoring_settings={"rec": 0.5, "bonus_rec_te": 0.5, "rush_fd": 1.0}
        )
    )

    fd_entry = next(entry for entry in scan.entries if entry.rule == "first_down_scoring")
    assert fd_entry.support_level == "partially_supported"
    assert scan.needs_acknowledgment is True


def test_non_dynasty_is_unsupported() -> None:
    scan = scan_league_format(_build_settings(settings_blob={"type": 0}))

    dynasty_entry = next(entry for entry in scan.entries if entry.rule == "non_dynasty")
    assert dynasty_entry.support_level == "unsupported"
    assert scan.league_unsupported is True


def test_waiver_budget_does_not_trigger_salary_cap() -> None:
    scan = scan_league_format(
        _build_settings(
            settings_blob={"type": 2, "waiver_budget": 200, "salary_cap": 0}
        )
    )

    assert all(entry.rule != "salary_cap" for entry in scan.entries)


def test_trust_modifier_full_support() -> None:
    assert compute_trust_modifier(scan_league_format(_build_settings()), False) == 1.0


def test_trust_modifier_partial_unacknowledged() -> None:
    scan = scan_league_format(
        _build_settings(settings_blob={"type": 2, "league_average_match": 1})
    )
    assert compute_trust_modifier(scan, False) == 0.75


def test_trust_modifier_unsupported() -> None:
    scan = scan_league_format(
        _build_settings(settings_blob={"type": 2, "best_ball": 1})
    )
    assert compute_trust_modifier(scan, True) == 0.5


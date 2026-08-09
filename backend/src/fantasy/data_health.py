"""Semantic health checks for statistical inputs used by decision models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import duckdb


MIN_CLONE_COMPARISON_ROWS = 100
CLONE_RATIO_THRESHOLD = 0.98
ROW_COUNT_RATIO_THRESHOLD = 0.98


@dataclass(frozen=True)
class SeasonProfile:
    season: int
    row_count: int
    player_count: int
    min_week: int
    max_week: int


@dataclass(frozen=True)
class StatsHealth:
    status: str
    integrity_status: str
    requested_league_season: int
    scoring_season: int | None
    scoring_status: str
    profiles: tuple[SeasonProfile, ...]
    issues: tuple[dict[str, Any], ...]
    model_version: str = "stats-health/1.0"

    def model_dump(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["profiles"] = [asdict(profile) for profile in self.profiles]
        payload["issues"] = list(self.issues)
        return payload


def _profiles(conn: duckdb.DuckDBPyConnection, league_season: int) -> list[SeasonProfile]:
    rows = conn.execute(
        """
        SELECT season, COUNT(*) AS row_count, COUNT(DISTINCT player_id) AS player_count,
               MIN(week) AS min_week, MAX(week) AS max_week
        FROM player_stats_weekly
        WHERE season <= ?
        GROUP BY season
        ORDER BY season DESC
        """,
        [league_season],
    ).fetchall()
    return [
        SeasonProfile(
            season=int(row[0]),
            row_count=int(row[1]),
            player_count=int(row[2]),
            min_week=int(row[3]),
            max_week=int(row[4]),
        )
        for row in rows
    ]


def _clone_evidence(
    conn: duckdb.DuckDBPyConnection,
    newer: SeasonProfile,
    older: SeasonProfile,
) -> dict[str, Any] | None:
    comparable, identical = conn.execute(
        """
        SELECT
            COUNT(*) AS comparable,
            COUNT(*) FILTER (
                WHERE n.fantasy_points IS NOT DISTINCT FROM o.fantasy_points
                  AND n.targets IS NOT DISTINCT FROM o.targets
                  AND n.carries IS NOT DISTINCT FROM o.carries
                  AND n.passing_yards IS NOT DISTINCT FROM o.passing_yards
                  AND n.receiving_yards IS NOT DISTINCT FROM o.receiving_yards
                  AND n.rushing_yards IS NOT DISTINCT FROM o.rushing_yards
            ) AS identical
        FROM player_stats_weekly n
        JOIN player_stats_weekly o
          ON o.player_id = n.player_id
         AND o.week = n.week
         AND o.season = ?
        WHERE n.season = ?
        """,
        [older.season, newer.season],
    ).fetchone()
    comparable = int(comparable or 0)
    identical = int(identical or 0)
    if comparable < MIN_CLONE_COMPARISON_ROWS:
        return None
    identical_ratio = identical / comparable
    row_count_ratio = min(newer.row_count, older.row_count) / max(
        newer.row_count, older.row_count
    )
    if (
        identical_ratio < CLONE_RATIO_THRESHOLD
        or row_count_ratio < ROW_COUNT_RATIO_THRESHOLD
    ):
        return None
    return {
        "code": "cross_season_clone",
        "severity": "blocking",
        "season": newer.season,
        "compared_with": older.season,
        "comparable_rows": comparable,
        "identical_rows": identical,
        "identical_ratio": round(identical_ratio, 4),
        "row_count_ratio": round(row_count_ratio, 4),
        "message": (
            f"Season {newer.season} is implausibly identical to {older.season}; "
            "it is excluded from scoring."
        ),
    }


def assess_stats_health(
    conn: duckdb.DuckDBPyConnection,
    league_season: int,
) -> StatsHealth:
    """Resolve a safe stats season and explain any excluded season payloads."""

    profiles = _profiles(conn, league_season)
    if not profiles:
        return StatsHealth(
            status="missing",
            integrity_status="unknown",
            requested_league_season=league_season,
            scoring_season=None,
            scoring_status="unavailable",
            profiles=(),
            issues=(
                {
                    "code": "stats_missing",
                    "severity": "blocking",
                    "message": "No weekly player statistics are available for scoring.",
                },
            ),
        )

    invalid_seasons: set[int] = set()
    issues: list[dict[str, Any]] = []
    for newer, older in zip(profiles, profiles[1:]):
        evidence = _clone_evidence(conn, newer, older)
        if evidence:
            invalid_seasons.add(newer.season)
            issues.append(evidence)

    selected = next(
        (profile.season for profile in profiles if profile.season not in invalid_seasons),
        None,
    )
    if selected is None:
        return StatsHealth(
            status="blocked",
            integrity_status="blocked_by_integrity_failure",
            requested_league_season=league_season,
            scoring_season=None,
            scoring_status="unavailable",
            profiles=tuple(profiles),
            issues=tuple(issues),
        )

    degraded = bool(invalid_seasons)
    return StatsHealth(
        status="degraded" if degraded else "valid",
        integrity_status=(
            "blocked_by_integrity_failure" if degraded else "passed"
        ),
        requested_league_season=league_season,
        scoring_season=selected,
        scoring_status="fallback_valid" if degraded else "selected_valid",
        profiles=tuple(profiles),
        issues=tuple(issues),
    )


def resolve_stats_season(
    conn: duckdb.DuckDBPyConnection,
    league_season: int,
) -> int | None:
    return assess_stats_health(conn, league_season).scoring_season

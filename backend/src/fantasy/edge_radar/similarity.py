from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import duckdb

from fantasy.edge_radar.models import SimilarPlayerOutcome


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def merge_context_metadata(
    metadata: dict[str, Any],
    context: dict[str, str | None],
) -> dict[str, Any]:
    merged = dict(metadata)
    for key, value in context.items():
        if value and not merged.get(key):
            merged[key] = value
    return merged


def team_context_from_row(
    row: tuple[Any, ...],
    start_index: int,
) -> dict[str, str | None]:
    keys = (
        "head_coach",
        "offensive_coordinator",
        "play_caller",
        "offensive_system",
        "pace_label",
        "pass_rate_label",
    )
    return {
        key: (
            str(row[start_index + offset])
            if row[start_index + offset] is not None
            else None
        )
        for offset, key in enumerate(keys)
    }


@dataclass(frozen=True)
class MetricSpec:
    key: str
    tolerance: float | None = None


@dataclass(frozen=True)
class MetricGroup:
    label: str
    weight: float
    specs: tuple[MetricSpec, ...]


@dataclass(frozen=True)
class SimilarityResult:
    score: float
    context: str


DENSE_GROUPS = (
    MetricGroup(
        "similar usage",
        0.16,
        (
            MetricSpec("target_share", 0.15),
            MetricSpec("air_yard_share", 0.15),
            MetricSpec("route_participation", 0.20),
            MetricSpec("snap_share", 0.20),
            MetricSpec("carry_share", 0.15),
            MetricSpec("red_zone_touches", 5.0),
        ),
    ),
    MetricGroup(
        "similar efficiency",
        0.10,
        (
            MetricSpec("yards_per_route_run", 1.0),
            MetricSpec("yards_after_catch", 4.0),
            MetricSpec("missed_tackles_forced", 5.0),
            MetricSpec("explosive_play_rate", 0.10),
            MetricSpec("epa_per_play", 0.30),
        ),
    ),
    MetricGroup(
        "similar role quality",
        0.14,
        (
            MetricSpec("first_read_target_share", 0.15),
            MetricSpec("slot_rate", 0.25),
            MetricSpec("wide_rate", 0.25),
            MetricSpec("goal_line_share", 0.10),
            MetricSpec("two_minute_snap_share", 0.25),
            MetricSpec("third_down_snap_share", 0.25),
        ),
    ),
    MetricGroup(
        "similar team environment",
        0.10,
        (
            MetricSpec("pass_rate_over_expectation", 0.10),
            MetricSpec("pace", 0.30),
            MetricSpec("play_volume", 15.0),
            MetricSpec("scoring_environment", 0.25),
            MetricSpec("offensive_line_strength", 0.25),
            MetricSpec("pace_label"),
            MetricSpec("pass_rate_label"),
        ),
    ),
    MetricGroup(
        "similar career stage",
        0.10,
        (
            MetricSpec("breakout_age", 3.0),
            MetricSpec("injury_games_missed", 6.0),
            MetricSpec("yoy_role_growth", 0.20),
        ),
    ),
    MetricGroup(
        "similar market behavior",
        0.12,
        (
            MetricSpec("adp_movement", 25.0),
            MetricSpec("trade_value_movement", 0.20),
            MetricSpec("roster_rate", 0.30),
            MetricSpec("waiver_add_rate", 0.20),
            MetricSpec("waiver_drop_rate", 0.20),
            MetricSpec("sentiment_lag", 0.30),
        ),
    ),
)

SYSTEM_KEYS = ("offensive_system", "head_coach", "offensive_coordinator", "play_caller")


def compute_similarity(
    *,
    team: str,
    age: int | None,
    metadata: dict[str, Any],
    model_value: float,
    market_price: float,
    role_stability: float,
    ceiling: float,
    floor: float,
    comp_team: str,
    comp_age: int | None,
    comp_metadata: dict[str, Any],
    comp_model_value: float,
    comp_market_price: float,
    comp_role_stability: float,
    comp_ceiling: float,
    comp_floor: float,
) -> SimilarityResult:
    weighted_score = 0.0
    available_weight = 0.0
    context_parts: list[str] = []

    if age is not None and comp_age is not None:
        age_score = max(0.0, 1.0 - (abs(age - comp_age) / 5.0))
        weighted_score += age_score * 0.10
        available_weight += 0.10
        if age_score >= 0.75:
            context_parts.append(f"age {comp_age}")

    value_distance = (
        abs(model_value - comp_model_value)
        + abs(market_price - comp_market_price)
        + abs(role_stability - comp_role_stability)
        + abs(ceiling - comp_ceiling)
        + abs(floor - comp_floor)
    ) / 5.0
    value_score = max(0.0, 1.0 - (value_distance / 0.35))
    weighted_score += value_score * 0.20
    available_weight += 0.20
    if value_score >= 0.75:
        context_parts.append("similar value and market price")

    if team and comp_team:
        team_score = 1.0 if team == comp_team else 0.0
        weighted_score += team_score * 0.05
        available_weight += 0.05
        if team_score >= 1.0:
            context_parts.append("same NFL team")

    system_matches = 0
    system_available = 0
    for key in SYSTEM_KEYS:
        if metadata.get(key) and comp_metadata.get(key):
            system_available += 1
            if metadata.get(key) == comp_metadata.get(key):
                system_matches += 1
    if system_available:
        system_score = system_matches / system_available
        weighted_score += system_score * 0.15
        available_weight += 0.15
        if metadata.get("offensive_system") == comp_metadata.get("offensive_system"):
            context_parts.append("same offensive system")
        if metadata.get("head_coach") == comp_metadata.get("head_coach"):
            context_parts.append("same head coach")
        if metadata.get("offensive_coordinator") == comp_metadata.get(
            "offensive_coordinator"
        ):
            context_parts.append("same offensive coordinator")

    for group in DENSE_GROUPS:
        group_score = _group_score(metadata, comp_metadata, group.specs)
        if group_score is None:
            continue
        weighted_score += group_score * group.weight
        available_weight += group.weight
        if group_score >= 0.75:
            context_parts.append(group.label)

    if not context_parts:
        context_parts.append("similar value and role profile")
    score = weighted_score / available_weight if available_weight else 0.0
    return SimilarityResult(score=clamp01(score), context=", ".join(context_parts))


def build_outcome_summary(
    *,
    avg_points: float | None,
    stat_games: int,
    model_value: float,
    market_price: float,
    next_four_week_points: float | None,
    rest_of_season_points: float | None,
    next_season_points: float | None,
    six_week_value_delta: float | None,
) -> str:
    parts: list[str] = []
    if next_four_week_points is not None:
        parts.append(f"next 4 weeks {next_four_week_points:.1f} fantasy points")
    if rest_of_season_points is not None:
        parts.append(f"rest of season {rest_of_season_points:.1f} fantasy points")
    if next_season_points is not None:
        parts.append(f"next season {next_season_points:.1f} fantasy points")
    if six_week_value_delta is not None:
        direction = "gained" if six_week_value_delta > 0 else "lost"
        parts.append(f"{direction} {six_week_value_delta:+.2f} value over next 6 weeks")
    if parts:
        return "; ".join(parts)
    if avg_points is not None and stat_games > 0:
        return (
            f"averaged {avg_points:.1f} fantasy points across "
            f"{stat_games} public stat games"
        )
    delta = model_value - market_price
    return (
        f"carried a {delta:+.2f} model-vs-market profile without "
        "public weekly outcome data"
    )


def value_gain_evidence(summaries: list[str]) -> list[str]:
    eligible = [
        summary
        for summary in summaries
        if "value over next 6 weeks" in summary
    ]
    if not eligible:
        return []
    gainers = [summary for summary in eligible if "gained +" in summary]
    rate = round((len(gainers) / len(eligible)) * 100.0)
    return [
        f"Outcome comps: {len(gainers)}/{len(eligible)} gained value over next 6 weeks ({rate}%)."
    ]


def similar_player_outcomes(
    conn: duckdb.DuckDBPyConnection,
    *,
    league_id: str,
    season: int | None,
    player_id: str,
    position: str,
    team: str,
    age: int | None,
    metadata: dict[str, Any],
    model_value: float,
    market_price: float,
    role_stability: float,
    ceiling: float,
    floor: float,
) -> list[SimilarPlayerOutcome]:
    rows = conn.execute(
        """
        SELECT p.player_id,
               COALESCE(p.full_name, p.player_id),
               COALESCE(p.position, 'UNKNOWN'),
               COALESCE(p.team, ''),
               p.age,
               p.metadata_blob,
               COALESCE(
                   pv.lens_production,
                   pv.lens_direction,
                   pv.comp_current_production,
                   0.5
               ),
               COALESCE(pv.lens_market, 0.5),
               COALESCE(pv.comp_role_stability, 0.5),
               COALESCE(pv.comp_ceiling, 0.5),
               COALESCE(pv.comp_floor, 0.5),
               AVG(ps.fantasy_points) AS avg_points,
               COUNT(ps.player_id) AS stat_games,
               AVG(ps.targets) AS avg_targets,
               AVG(ps.carries) AS avg_carries,
               AVG(
                   CASE
                       WHEN (? IS NOT NULL AND ps.season = ? AND ps.week BETWEEN 1 AND 4)
                       THEN ps.fantasy_points
                       ELSE NULL
                   END
               ) AS next_four_week_points,
               AVG(
                   CASE
                       WHEN (? IS NOT NULL AND ps.season = ?)
                       THEN ps.fantasy_points
                       ELSE NULL
                   END
               ) AS rest_of_season_points,
               AVG(
                   CASE
                       WHEN (? IS NOT NULL AND ps.season = ?)
                       THEN ps.fantasy_points
                       ELSE NULL
                   END
               ) AS next_season_points,
               tc.head_coach,
               tc.offensive_coordinator,
               tc.play_caller,
               tc.offensive_system,
               tc.pace_label,
               tc.pass_rate_label
        FROM players p
        JOIN player_values pv ON pv.player_id = p.player_id
        LEFT JOIN player_stats_weekly ps ON ps.player_id = p.player_id
        LEFT JOIN team_context_by_season tc
          ON tc.team = p.team
         AND (? IS NOT NULL AND tc.season = ?)
        WHERE p.player_id != ?
          AND COALESCE(p.position, 'UNKNOWN') = ?
          AND pv.league_id = ?
        GROUP BY p.player_id, p.full_name, p.position, p.team, p.age, p.metadata_blob,
                 pv.lens_production, pv.lens_direction, pv.comp_current_production,
                 pv.lens_market, pv.comp_role_stability, pv.comp_ceiling, pv.comp_floor,
                 tc.head_coach, tc.offensive_coordinator, tc.play_caller,
                 tc.offensive_system, tc.pace_label, tc.pass_rate_label
        LIMIT 80
        """,
        [
            season,
            season,
            season,
            season,
            season + 1 if season is not None else None,
            season + 1 if season is not None else None,
            season,
            season,
            player_id,
            position,
            league_id,
        ],
    ).fetchall()
    outcomes: list[SimilarPlayerOutcome] = []
    for row in rows:
        comp_metadata = merge_context_metadata(
            _loads(row[5], {}),
            team_context_from_row(row, 18),
        )
        if row[13] is not None and not comp_metadata.get("weekly_targets"):
            comp_metadata["weekly_targets"] = float(row[13])
        if row[14] is not None and not comp_metadata.get("weekly_carries"):
            comp_metadata["weekly_carries"] = float(row[14])
        similarity = compute_similarity(
            team=team,
            age=age,
            metadata=metadata,
            model_value=model_value,
            market_price=market_price,
            role_stability=role_stability,
            ceiling=ceiling,
            floor=floor,
            comp_team=str(row[3] or ""),
            comp_age=int(row[4]) if row[4] is not None else None,
            comp_metadata=comp_metadata,
            comp_model_value=clamp01(float(row[6] or 0.5)),
            comp_market_price=clamp01(float(row[7] or 0.5)),
            comp_role_stability=clamp01(float(row[8] or 0.5)),
            comp_ceiling=clamp01(float(row[9] or 0.5)),
            comp_floor=clamp01(float(row[10] or 0.5)),
        )
        if similarity.score < 0.45:
            continue
        outcomes.append(
            SimilarPlayerOutcome(
                player_id=str(row[0]),
                player_name=str(row[1]),
                similarity_score=round(similarity.score, 2),
                context=similarity.context,
                outcome_summary=build_outcome_summary(
                    avg_points=float(row[11]) if row[11] is not None else None,
                    stat_games=int(row[12] or 0),
                    model_value=clamp01(float(row[6] or 0.5)),
                    market_price=clamp01(float(row[7] or 0.5)),
                    next_four_week_points=(
                        float(row[15]) if row[15] is not None else None
                    ),
                    rest_of_season_points=(
                        float(row[16]) if row[16] is not None else None
                    ),
                    next_season_points=(
                        float(row[17]) if row[17] is not None else None
                    ),
                    six_week_value_delta=metadata_float(
                        comp_metadata,
                        "six_week_value_delta",
                    ),
                ),
            )
        )
    outcomes.sort(key=lambda outcome: (-outcome.similarity_score, outcome.player_name))
    return outcomes[:3]


def metadata_float(metadata: dict[str, Any], key: str) -> float | None:
    value = metadata.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _group_score(
    metadata: dict[str, Any],
    comp_metadata: dict[str, Any],
    specs: tuple[MetricSpec, ...],
) -> float | None:
    scores: list[float] = []
    for spec in specs:
        target_value = metadata.get(spec.key)
        comp_value = comp_metadata.get(spec.key)
        if target_value in (None, "") or comp_value in (None, ""):
            continue
        if spec.tolerance is None:
            scores.append(1.0 if str(target_value) == str(comp_value) else 0.0)
            continue
        try:
            distance = abs(float(target_value) - float(comp_value))
        except (TypeError, ValueError):
            continue
        scores.append(max(0.0, 1.0 - (distance / spec.tolerance)))
    if not scores:
        return None
    return sum(scores) / len(scores)


__all__ = [
    "SimilarityResult",
    "build_outcome_summary",
    "clamp01",
    "compute_similarity",
    "merge_context_metadata",
    "metadata_float",
    "similar_player_outcomes",
    "team_context_from_row",
    "value_gain_evidence",
]

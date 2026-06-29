from __future__ import annotations

import json
import math
from datetime import datetime, timedelta
from typing import Any, Literal

import duckdb
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from fantasy.config import get_settings
from fantasy.context.calendar_service import CalendarService
from fantasy.context.constants import CALENDAR_GUIDANCE
from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.context.models import RecommendationContext
from fantasy.intelligence.constants import DIRECTION_WEIGHTS, REBUILD_DIRECTION_LABELS
from fantasy.routers.deps import get_read_db_conn

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

RECENT_EXPLOIT_WINDOW_DAYS = 14
RECENT_TRADEABILITY_DAYS = 90

SCORECARD_FIELDS = [
    "win_now",
    "future_value",
    "depth",
    "pick_capital",
    "flexibility",
    "fragility",
    "age_risk",
    "liquidity",
    "positional_insulation",
]

SUMMARY_SIGNAL_FIELDS = [
    "pick_capital",
    "win_now",
    "future_value",
    "liquidity",
    "depth",
    "positional_insulation",
]

SUMMARY_SIGNAL_EDGE_LABELS: dict[str, str] = {
    "pick_capital": "Pick capital edge",
    "win_now": "Win-now edge",
    "future_value": "Future value edge",
    "liquidity": "Market liquidity edge",
    "depth": "Depth edge",
    "positional_insulation": "Lineup insulation edge",
}

SUMMARY_SIGNAL_NEUTRAL_LABELS: dict[str, str] = {
    "pick_capital": "Best relative score: pick capital",
    "win_now": "Best relative score: win now",
    "future_value": "Best relative score: future value",
    "liquidity": "Best relative score: market liquidity",
    "depth": "Best relative score: depth",
    "positional_insulation": "Best relative score: lineup insulation",
}

WEAKNESS_LABELS: dict[str, str] = {
    "win_now": "Your lineup needs more weekly production to compete now.",
    "future_value": "Your roster lacks enough insulated long-term value.",
    "depth": "You need more playable depth behind your starters.",
    "pick_capital": "You need more draft capital to unlock flexible moves.",
    "flexibility": "Position mix is skewed toward one position group.",
    "fragility": "You have too many brittle weekly outcomes right now.",
    "age_risk": "Your core is carrying too much age-related downside.",
    "liquidity": "You need more liquid market assets to move when needed.",
    "positional_insulation": "You need more insulation at scarce lineup spots.",
}

HIGHER_IS_WORSE_FIELDS = {"fragility", "age_risk"}

DirectionReadBand = Literal["Clear", "Leaning", "Hybrid", "Tentative", "--"]
_HYBRID_DIRECTION_GAP = 0.02
_DIRECTION_DIMENSION_LABELS: dict[str, str] = {
    "win_now": "Win-Now Output",
    "future_value": "Future Value",
    "depth": "Depth",
    "pick_capital": "Pick Capital",
    "flexibility": "Flexibility",
    "fragility": "Fragility",
    "age_risk": "Age Risk",
    "liquidity": "Liquidity",
    "positional_insulation": "Positional Insulation",
}

_DIRECTION_DIMENSION_STATE_COPY: dict[str, dict[str, str]] = {
    "win_now": {
        "high": "Weekly production is still a real part of this roster.",
        "mixed": "The roster can score now without forcing a full win-now posture.",
        "low": "Immediate lineup output is limited.",
    },
    "future_value": {
        "high": "Insulated future value is clearly present.",
        "mixed": "Future value exists, but it is not the whole story.",
        "low": "Long-term insulation is thin.",
    },
    "depth": {
        "high": "The roster has playable depth behind the starters.",
        "mixed": "Depth is serviceable without being a major edge.",
        "low": "Depth falls off quickly behind the main pieces.",
    },
    "pick_capital": {
        "high": "Draft capital gives this roster extra optionality.",
        "mixed": "Pick leverage is present, but not decisive.",
        "low": "Pick capital is limited.",
    },
    "flexibility": {
        "high": "The roster has multiple ways to pivot its next move.",
        "mixed": "Some pivots are available, but the build is not fully open-ended.",
        "low": "The roster is more locked into its current shape.",
    },
    "fragility": {
        "high": "Week-to-week outcomes look volatile and narrow.",
        "mixed": "There is some fragility, but it does not define the whole roster.",
        "low": "The roster is relatively insulated from brittle weekly outcomes.",
    },
    "age_risk": {
        "high": "The core carries visible age-related downside.",
        "mixed": "Some age pressure exists, but it is not overwhelming.",
        "low": "Age-related downside is fairly contained.",
    },
    "liquidity": {
        "high": "This roster holds assets that should stay movable in the market.",
        "mixed": "Some market liquidity is present, but not across the whole core.",
        "low": "The roster has fewer clean market exits if you need to pivot.",
    },
    "positional_insulation": {
        "high": "Scarce lineup spots are relatively protected.",
        "mixed": "Insulation exists at key spots, but not across the full lineup.",
        "low": "Scarce lineup spots are still exposed.",
    },
}

_DIRECTION_DIMENSION_DESIRES: dict[str, dict[str, str]] = {
    "win_now": {
        "higher": "usable current-season output",
        "lower": "less immediate scoring pressure",
    },
    "future_value": {
        "higher": "future leverage",
        "lower": "less dependence on future insulation",
    },
    "depth": {
        "higher": "playable depth",
        "lower": "less reliance on bench depth",
    },
    "pick_capital": {
        "higher": "pick leverage",
        "lower": "less dependence on draft capital",
    },
    "flexibility": {
        "higher": "roster optionality",
        "lower": "a more committed roster shape",
    },
    "fragility": {
        "higher": "volatility and narrow weekly paths",
        "lower": "less fragility risk",
    },
    "age_risk": {
        "higher": "age pressure on the core",
        "lower": "less age-cliff exposure",
    },
    "liquidity": {
        "higher": "market liquidity",
        "lower": "less dependence on tradable liquidity",
    },
    "positional_insulation": {
        "higher": "lineup insulation at scarce spots",
        "lower": "less insulation-driven roster value",
    },
}


class DashboardLeagueSummary(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    league_name: str
    user_roster_id: int | None = None
    direction_label: str
    confidence_band: Literal["High", "Medium", "Low", "--"]
    direction_read: DirectionReadBand = "--"
    direction_alternates: list[str] = Field(default_factory=list)
    direction_note: str | None = None
    summary_signal: str
    primary_weakness: str
    top_exploit_window: str | None = None
    last_snapshot_at: str | None = None
    last_ingest_at: str | None = None


class LeagueRosterOption(BaseModel):
    model_config = ConfigDict(frozen=False)

    roster_id: int
    owner_id: str | None = None
    owner_display_name: str | None = None
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: float = 0.0


class RiserFallerEntry(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_name: str
    delta: float
    reason: str


class PlayerRankingEntry(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_id: str
    player_name: str
    position: str
    team: str | None = None
    age: int | None = None
    roster_id: int
    owner_name: str
    is_user_roster: bool = False
    rank: int
    position_rank: int
    tier: int
    rank_score: float
    lens_market: float | None = None
    lens_production: float | None = None
    lens_insulation: float | None = None
    lens_direction: float | None = None
    fantasycalc_rank: int | None = None
    fantasycalc_value: float | None = None
    trend_30day: float | None = None


class PlayerRankingsResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    rankings: list[PlayerRankingEntry]


class ExploitTrigger(BaseModel):
    model_config = ConfigDict(frozen=False)

    type: str
    description: str
    suggested_action: str


class ExploitWindowManager(BaseModel):
    model_config = ConfigDict(frozen=False)

    roster_id: int
    manager_name: str | None = None
    trigger_count: int
    is_high_opportunity: bool
    triggers: list[ExploitTrigger]


class DirectionFitFlag(BaseModel):
    model_config = ConfigDict(frozen=False)

    dimension: str
    label: str
    strength: Literal["Strong Fit", "Supporting", "Secondary"]
    detail: str


class ComparativeMetricSummary(BaseModel):
    model_config = ConfigDict(frozen=False)

    key: Literal["win_now", "future_value", "title_window"]
    label: str
    rank: int
    league_size: int
    score: float
    gap_to_leader: float
    edge_vs_median: float


class PowerRankingEntry(BaseModel):
    model_config = ConfigDict(frozen=False)

    roster_id: int
    manager_name: str
    rank: int
    score: float
    is_user: bool = False
    direction_label: str | None = None
    title_window_label: str | None = None
    record: str | None = None


class MatchupPrediction(BaseModel):
    model_config = ConfigDict(frozen=False)

    roster_id: int
    manager_name: str
    win_probability: float
    verdict: Literal["favored", "toss_up", "underdog"]
    reason: str


class LeagueCompetitiveLandscape(BaseModel):
    model_config = ConfigDict(frozen=False)

    metric_summaries: list[ComparativeMetricSummary] = Field(default_factory=list)
    win_now_rankings: list[PowerRankingEntry] = Field(default_factory=list)
    future_value_rankings: list[PowerRankingEntry] = Field(default_factory=list)
    title_window_rankings: list[PowerRankingEntry] = Field(default_factory=list)
    matchup_predictions: list[MatchupPrediction] = Field(default_factory=list)


class LeagueDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    league_name: str
    user_roster_id: int | None = None
    user_roster_name: str | None = None
    user_owner_id: str | None = None
    user_roster_player_ids: list[str] = Field(default_factory=list)
    direction_label: str
    confidence_band: Literal["High", "Medium", "Low", "--"]
    direction_read: DirectionReadBand = "--"
    direction_alternates: list[str] = Field(default_factory=list)
    direction_note: str | None = None
    direction_reasoning: str | None = None
    direction_fit_flags: list[DirectionFitFlag] = Field(default_factory=list)
    primary_weakness: str
    risers: list[RiserFallerEntry]
    fallers: list[RiserFallerEntry]
    exploit_windows: list[ExploitWindowManager]
    last_snapshot_at: str | None = None
    last_ingest_at: str | None = None
    recommendation_context: RecommendationContext | None = None
    competitive_landscape: LeagueCompetitiveLandscape | None = None


def _build_recommendation_context(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
) -> RecommendationContext:
    repo = ContextRepo(conn)
    calendar_context = CalendarService(repo=repo).get_context(league_id)
    freshness_tags = FreshnessService(repo=repo).get_tags(
        league_id,
        ["injuries", "depth_chart", "free_agency"],
    )
    note = CALENDAR_GUIDANCE.get((calendar_context.active_state, "general"))
    return RecommendationContext(
        calendar_state=calendar_context.active_state,
        freshness_tags=[tag for tag in freshness_tags if tag.is_stale],
        calendar_note=note,
    )


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _band(confidence: float | None) -> Literal["High", "Medium", "Low", "--"]:
    if confidence is None:
        return "--"
    if confidence >= 0.7:
        return "High"
    if confidence >= 0.4:
        return "Medium"
    return "Low"


def _format_model_label(value: str) -> str:
    return " ".join(
        part.capitalize()
        for part in value.replace("-", "_").split("_")
        if part
    )


def _alternate_labels(alternates: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for alternate in alternates:
        label = str(alternate.get("label", "")).strip()
        if not label or label in labels:
            continue
        labels.append(label)
    return labels


def _hybrid_alternates(alternates: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for alternate in alternates:
        label = str(alternate.get("label", "")).strip()
        if not label or label in labels:
            continue
        try:
            gap = float(alternate.get("gap", 1.0))
        except (TypeError, ValueError):
            gap = 1.0
        if gap <= _HYBRID_DIRECTION_GAP:
            labels.append(label)
    return labels


def _join_direction_labels(labels: list[str]) -> str:
    formatted = [_format_model_label(label) for label in labels]
    if not formatted:
        return ""
    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]} and {formatted[1]}"
    return f"{', '.join(formatted[:-1])}, and {formatted[-1]}"


def _direction_read(
    confidence: float | None,
    alternates: list[dict[str, Any]],
) -> DirectionReadBand:
    if confidence is None:
        return "--"
    if _hybrid_alternates(alternates):
        return "Hybrid"
    if confidence >= 0.7:
        return "Clear"
    if confidence >= 0.4:
        return "Leaning"
    return "Tentative"


def _direction_note(
    direction_label: str,
    direction_read: DirectionReadBand,
    alternates: list[dict[str, Any]],
) -> str | None:
    formatted_primary = _format_model_label(direction_label)
    close_alternates = _hybrid_alternates(alternates)
    all_alternates = _alternate_labels(alternates)
    if direction_read == "--":
        return None
    if direction_read == "Hybrid":
        mix = _join_direction_labels([direction_label, *close_alternates[:2]])
        return f"Hybrid read: this roster sits between {mix}."
    if direction_read == "Clear":
        return f"Clear read: {formatted_primary} stands apart from the nearby roster paths."
    if direction_read == "Leaning" and all_alternates:
        return (
            f"Leaning read: {formatted_primary} leads, "
            f"with {_format_model_label(all_alternates[0])} as the closest alternate."
        )
    if direction_read == "Tentative":
        return (
            f"Tentative read: {formatted_primary} leads, but the roster shape still "
            "needs more separation from the rest of the board."
        )
    return f"Leaning read: {formatted_primary} currently has the strongest signal."


def _bucket_label(value: float) -> str:
    if value >= 0.67:
        return "High"
    if value <= 0.33:
        return "Low"
    return "Mixed"


def _fit_strength(value: float) -> Literal["Strong Fit", "Supporting", "Secondary"]:
    if value >= 0.72:
        return "Strong Fit"
    if value >= 0.55:
        return "Supporting"
    return "Secondary"


def _band_phrase(value: float) -> str:
    if value >= 0.67:
        return "high"
    if value <= 0.33:
        return "low"
    return "mixed"


def _team_specific_flag_detail(
    direction_label: str,
    dimension: str,
    value: float,
    scorecard: dict[str, float],
) -> str:
    formatted_direction = _format_model_label(direction_label)
    score_text = f"{value:.2f}"

    if dimension == "future_value":
        return (
            f"Future value grades as {_band_phrase(value)} on this roster's scorecard ({score_text}). "
            f"There is some forward insulation here, but with win-now output at "
            f"{scorecard['win_now']:.2f} and pick capital at {scorecard['pick_capital']:.2f}, "
            f"the team still looks like a {formatted_direction} build instead of a pure stash-and-wait roster."
        )
    if dimension == "win_now":
        return (
            f"Win-now output is {_band_phrase(value)} for this roster ({score_text}). "
            f"The current lineup can still post points, which is why this team does not read like a full tear-down, "
            f"even with future value at {scorecard['future_value']:.2f}."
        )
    if dimension == "liquidity":
        return (
            f"Liquidity comes in {_band_phrase(value)} on this roster ({score_text}). "
            f"There are enough movable assets here to pivot if the market opens, which supports a {formatted_direction} lane "
            f"without forcing an all-in push."
        )
    if dimension == "pick_capital":
        return (
            f"Pick capital shows as {_band_phrase(value)} for this roster ({score_text}). "
            f"That gives the team some future leverage, but not enough by itself to overpower the current roster direction."
        )
    if dimension == "depth":
        return (
            f"Depth grades {_band_phrase(value)} for this team ({score_text}). "
            f"The roster has enough playable support pieces to stay functional, but depth is not carrying the identity of the build."
        )
    if dimension == "flexibility":
        return (
            f"Flexibility lands in the {_band_phrase(value)} range for this roster ({score_text}). "
            f"The team has multiple pivot paths, but it is not so open-ended that the direction becomes undefined."
        )
    if dimension == "fragility":
        return (
            f"Fragility grades {_band_phrase(value)} on this roster ({score_text}). "
            f"That tells you how narrow the weekly margin is: lower fragility supports this direction, while higher fragility would push it toward a thinner, shakier read."
        )
    if dimension == "age_risk":
        return (
            f"Age risk comes in {_band_phrase(value)} for this core ({score_text}). "
            f"That matters because this roster is balancing current output with how quickly the value base could decay."
        )
    if dimension == "positional_insulation":
        return (
            f"Positional insulation reads {_band_phrase(value)} for this roster ({score_text}). "
            f"Scarce lineup spots are protected enough to keep the build stable, but not so insulated that the team jumps into a cleaner contender bucket."
        )

    return (
        f"{_DIRECTION_DIMENSION_LABELS.get(dimension, dimension.replace('_', ' ').title())} "
        f"grades as {_band_phrase(value)} for this roster ({score_text}), which helps explain the "
        f"{formatted_direction} read."
    )


def _direction_fit_flags(
    direction_label: str,
    scorecard_row: tuple[Any, ...] | None,
) -> list[DirectionFitFlag]:
    if scorecard_row is None:
        return []
    weights = DIRECTION_WEIGHTS.get(direction_label)
    if weights is None:
        return []

    scorecard = {
        field: float(value)
        for field, value in zip(SCORECARD_FIELDS, scorecard_row, strict=False)
    }

    ranked_dimensions = sorted(
        scorecard.items(),
        key=lambda item: abs(weights.get(item[0], 0.0))
        * (
            item[1]
            if weights.get(item[0], 0.0) >= 0.0
            else 1.0 - item[1]
        ),
        reverse=True,
    )

    flags: list[DirectionFitFlag] = []
    for dimension, value in ranked_dimensions:
        weight = weights.get(dimension, 0.0)
        if abs(weight) < 1e-9:
            continue
        fit_value = value if weight >= 0.0 else 1.0 - value
        desired_key = "higher" if weight >= 0.0 else "lower"
        level = _bucket_label(value).lower()
        dimension_label = _DIRECTION_DIMENSION_LABELS.get(
            dimension,
            dimension.replace("_", " ").title(),
        )
        detail = " ".join(
            [
                _team_specific_flag_detail(direction_label, dimension, value, scorecard),
                _DIRECTION_DIMENSION_STATE_COPY[dimension][level],
                f"{_format_model_label(direction_label)} fits when the roster shows "
                f"{_DIRECTION_DIMENSION_DESIRES[dimension][desired_key]}.",
            ]
        )
        flags.append(
            DirectionFitFlag(
                dimension=dimension,
                label=f"{_bucket_label(value)} {dimension_label}",
                strength=_fit_strength(fit_value),
                detail=detail,
            )
        )
        if len(flags) == 3:
            break
    return flags


def _ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _derive_summary_signal(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    roster_id: int,
    scorecard_row: tuple[Any, ...] | None,
) -> str:
    if scorecard_row is None:
        return "Run Phase 2 intelligence to surface your top edge."

    scorecard = {
        field: float(value)
        for field, value in zip(SCORECARD_FIELDS, scorecard_row, strict=False)
    }

    best_field = SUMMARY_SIGNAL_FIELDS[0]
    best_value = scorecard.get(best_field, 0.0)
    for field in SUMMARY_SIGNAL_FIELDS[1:]:
        value = scorecard.get(field, 0.0)
        if value > best_value:
            best_field = field
            best_value = value

    rows = conn.execute(
        f"""
        SELECT roster_id, {best_field}
        FROM team_scorecards
        WHERE league_id = ?
        ORDER BY {best_field} DESC, roster_id ASC
        """,
        [league_id],
    ).fetchall()
    if not rows:
        return "Run Phase 2 intelligence to surface your top edge."

    rank = next(
        (index for index, (candidate_roster_id, _value) in enumerate(rows, start=1) if int(candidate_roster_id) == roster_id),
        None,
    )
    if rank is None:
        return "Run Phase 2 intelligence to surface your top edge."

    league_size = len(rows)
    edge_cutoff = max(3, (league_size + 3) // 4)
    rank_label = _ordinal(rank)
    if rank <= edge_cutoff:
        label = SUMMARY_SIGNAL_EDGE_LABELS[best_field]
        return f"{label}: {rank_label} of {league_size} in this league."

    label = SUMMARY_SIGNAL_NEUTRAL_LABELS[best_field]
    return f"{label} is {rank_label} of {league_size} in this league."


def _median_value(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 != 0:
        return float(ordered[midpoint])
    return float((ordered[midpoint - 1] + ordered[midpoint]) / 2)


def _record_label(
    wins: int | None,
    losses: int | None,
    ties: int | None,
) -> str | None:
    if wins is None or losses is None:
        return None
    if ties is None or ties == 0:
        return f"{wins}-{losses}"
    return f"{wins}-{losses}-{ties}"


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _title_target_attainment_score(
    total_lineup_score: float | None,
    title_target: float | None,
    elite_target: float | None,
) -> float:
    if total_lineup_score is None or title_target is None or title_target <= 0:
        return 0.0
    if total_lineup_score < title_target:
        return _clamp01((total_lineup_score / title_target) * 0.72)
    if elite_target is None or elite_target <= title_target:
        return 0.9
    elite_progress = _clamp01((total_lineup_score - title_target) / (elite_target - title_target))
    return 0.78 + elite_progress * 0.22


def _league_competition_rows(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT
            r.roster_id,
            COALESCE(
                NULLIF(r.owner_display_name, ''),
                NULLIF(r.owner_id, ''),
                'Roster ' || CAST(r.roster_id AS VARCHAR)
            ) AS manager_name,
            td.primary_label,
            ts.win_now,
            ts.future_value,
            ls.title_window_composite,
            ls.title_window_label,
            ls.ceiling_score,
            ls.stability_score,
            ls.depth_score,
            ls.total_lineup_score,
            ls.overall_title_target,
            ls.overall_elite_target,
            ts.pick_capital,
            ts.age_risk,
            st.wins,
            st.losses,
            st.ties
        FROM rosters r
        LEFT JOIN team_directions td
            ON td.league_id = r.league_id AND td.roster_id = r.roster_id
        LEFT JOIN team_scorecards ts
            ON ts.league_id = r.league_id AND ts.roster_id = r.roster_id
        LEFT JOIN lineup_scores ls
            ON ls.league_id = r.league_id AND ls.roster_id = r.roster_id
        LEFT JOIN standings st
            ON st.league_id = r.league_id AND st.roster_id = r.roster_id
        WHERE r.league_id = ?
        ORDER BY r.roster_id
        """,
        [league_id],
    ).fetchall()

    competition_rows: list[dict[str, Any]] = []
    max_lineup_score = max(
        (float(row[10]) for row in rows if row[10] is not None),
        default=0.0,
    )
    for row in rows:
        wins = int(row[15]) if row[15] is not None else None
        losses = int(row[16]) if row[16] is not None else None
        ties = int(row[17]) if row[17] is not None else None
        total_lineup_score = float(row[10]) if row[10] is not None else None
        title_target = float(row[11]) if row[11] is not None else None
        elite_target = float(row[12]) if row[12] is not None else None
        title_composite = float(row[5]) if row[5] is not None else None
        future_value = float(row[4]) if row[4] is not None else None
        pick_capital = float(row[13]) if row[13] is not None else None
        age_risk = float(row[14]) if row[14] is not None else None
        future_insulation = (
            _clamp01(
                (
                    (future_value or 0.0)
                    + (pick_capital or 0.0)
                    + max(0.0, 1.0 - (age_risk or 0.0))
                )
                / 3.0
            )
            if future_value is not None or pick_capital is not None or age_risk is not None
            else 0.0
        )
        lineup_power = (
            _clamp01(total_lineup_score / max_lineup_score)
            if total_lineup_score is not None and max_lineup_score > 0
            else 0.0
        )
        title_window_score = (
            lineup_power * 0.55
            + _title_target_attainment_score(total_lineup_score, title_target, elite_target) * 0.25
            + (title_composite or 0.0) * 0.10
            + future_insulation * 0.10
        )
        competition_rows.append(
            {
                "roster_id": int(row[0]),
                "manager_name": str(row[1]),
                "direction_label": str(row[2]) if row[2] is not None else None,
                "win_now": float(row[3]) if row[3] is not None else None,
                "future_value": future_value,
                "title_window": title_window_score,
                "title_window_label": str(row[6]) if row[6] is not None else None,
                "ceiling_score": float(row[7]) if row[7] is not None else None,
                "stability_score": float(row[8]) if row[8] is not None else None,
                "depth_score": float(row[9]) if row[9] is not None else None,
                "record": _record_label(wins, losses, ties),
            }
        )
    return competition_rows


def _rank_metric_rows(
    rows: list[dict[str, Any]],
    key: Literal["win_now", "future_value", "title_window"],
) -> list[dict[str, Any]]:
    ranked = [row for row in rows if row.get(key) is not None]
    return sorted(
        ranked,
        key=lambda row: (-float(row[key]), int(row["roster_id"])),
    )


def _build_metric_summary(
    rows: list[dict[str, Any]],
    user_roster_id: int,
    key: Literal["win_now", "future_value", "title_window"],
    label: str,
) -> ComparativeMetricSummary | None:
    ranked = _rank_metric_rows(rows, key)
    if not ranked:
        return None

    user_row = next((row for row in ranked if int(row["roster_id"]) == user_roster_id), None)
    if user_row is None:
        return None

    user_score = float(user_row[key])
    values = [float(row[key]) for row in ranked]
    leader_score = float(values[0])
    median_score = _median_value(values)
    rank = next(
        index
        for index, row in enumerate(ranked, start=1)
        if int(row["roster_id"]) == user_roster_id
    )
    return ComparativeMetricSummary(
        key=key,
        label=label,
        rank=rank,
        league_size=len(ranked),
        score=round(user_score, 3),
        gap_to_leader=round(max(0.0, leader_score - user_score), 3),
        edge_vs_median=round(user_score - median_score, 3),
    )


def _build_power_rankings(
    rows: list[dict[str, Any]],
    user_roster_id: int | None,
    key: Literal["win_now", "future_value", "title_window"],
) -> list[PowerRankingEntry]:
    ranked = _rank_metric_rows(rows, key)
    return [
        PowerRankingEntry(
            roster_id=int(row["roster_id"]),
            manager_name=str(row["manager_name"]),
            rank=index,
            score=round(float(row[key]), 3),
            is_user=user_roster_id is not None and int(row["roster_id"]) == user_roster_id,
            direction_label=str(row["direction_label"]) if row["direction_label"] else None,
            title_window_label=(
                str(row["title_window_label"]) if row["title_window_label"] else None
            ),
            record=str(row["record"]) if row["record"] else None,
        )
        for index, row in enumerate(ranked, start=1)
    ]


def _join_phrases(parts: list[str]) -> str:
    cleaned = [part.strip() for part in parts if part.strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"


def _matchup_reason(components: dict[str, float]) -> str:
    labels = {
        "title_window": "title-window strength",
        "ceiling": "ceiling",
        "stability": "weekly stability",
        "depth": "depth",
        "win_now": "win-now base",
    }
    positives = [
        labels[key]
        for key, value in sorted(components.items(), key=lambda item: abs(item[1]), reverse=True)
        if value > 0.03
    ]
    negatives = [
        labels[key]
        for key, value in sorted(components.items(), key=lambda item: abs(item[1]), reverse=True)
        if value < -0.03
    ]
    if positives and not negatives:
        return f"Your edge comes from stronger {_join_phrases(positives[:2])}."
    if negatives and not positives:
        return f"This opponent currently has the better {_join_phrases(negatives[:2])}."
    if positives and negatives:
        return (
            f"You lead in {positives[0]}, but they answer with better {negatives[0]}."
        )
    return "These rosters project close across ceiling, stability, and depth."


def _build_matchup_predictions(
    rows: list[dict[str, Any]],
    user_roster_id: int,
) -> list[MatchupPrediction]:
    user_row = next((row for row in rows if int(row["roster_id"]) == user_roster_id), None)
    if user_row is None:
        return []
    required_keys = ("title_window", "ceiling_score", "stability_score", "depth_score")
    if any(user_row.get(key) is None for key in required_keys):
        return []

    predictions: list[MatchupPrediction] = []
    for opponent in rows:
        if int(opponent["roster_id"]) == user_roster_id:
            continue
        if any(opponent.get(key) is None for key in required_keys):
            continue

        components = {
            "title_window": float(user_row["title_window"]) - float(opponent["title_window"]),
            "ceiling": float(user_row["ceiling_score"]) - float(opponent["ceiling_score"]),
            "stability": float(user_row["stability_score"]) - float(opponent["stability_score"]),
            "depth": float(user_row["depth_score"]) - float(opponent["depth_score"]),
            "win_now": (
                float(user_row["win_now"]) - float(opponent["win_now"])
                if user_row.get("win_now") is not None and opponent.get("win_now") is not None
                else 0.0
            ),
        }
        matchup_edge = (
            1.35 * components["title_window"]
            + 0.8 * components["ceiling"]
            + 0.6 * components["stability"]
            + 0.45 * components["depth"]
            + 0.35 * components["win_now"]
        )
        win_probability = 1.0 / (1.0 + math.exp(-(matchup_edge * 2.25)))
        if win_probability >= 0.6:
            verdict: Literal["favored", "toss_up", "underdog"] = "favored"
        elif win_probability <= 0.4:
            verdict = "underdog"
        else:
            verdict = "toss_up"
        predictions.append(
            MatchupPrediction(
                roster_id=int(opponent["roster_id"]),
                manager_name=str(opponent["manager_name"]),
                win_probability=round(win_probability, 3),
                verdict=verdict,
                reason=_matchup_reason(components),
            )
        )

    return sorted(
        predictions,
        key=lambda prediction: (prediction.win_probability, prediction.roster_id),
    )


def _build_competitive_landscape(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    user_roster_id: int | None,
) -> LeagueCompetitiveLandscape | None:
    if user_roster_id is None:
        return None

    rows = _league_competition_rows(conn, league_id)
    if not rows:
        return None

    metric_summaries = [
        summary
        for summary in (
            _build_metric_summary(rows, user_roster_id, "win_now", "Win Now"),
            _build_metric_summary(rows, user_roster_id, "future_value", "Future Value"),
            _build_metric_summary(rows, user_roster_id, "title_window", "Title Window"),
        )
        if summary is not None
    ]
    win_now_rankings = _build_power_rankings(rows, user_roster_id, "win_now")
    future_value_rankings = _build_power_rankings(rows, user_roster_id, "future_value")
    title_window_rankings = _build_power_rankings(rows, user_roster_id, "title_window")
    matchup_predictions = _build_matchup_predictions(rows, user_roster_id)

    if (
        not metric_summaries
        and not win_now_rankings
        and not future_value_rankings
        and not title_window_rankings
        and not matchup_predictions
    ):
        return None

    return LeagueCompetitiveLandscape(
        metric_summaries=metric_summaries,
        win_now_rankings=win_now_rankings,
        future_value_rankings=future_value_rankings,
        title_window_rankings=title_window_rankings,
        matchup_predictions=matchup_predictions,
    )


def _position_group_phrase(position: str, count: int) -> tuple[str, str]:
    labels = {
        "QB": ("QB", "QBs"),
        "RB": ("RB", "RBs"),
        "WR": ("WR", "WRs"),
        "TE": ("TE", "TEs"),
        "K": ("K", "Ks"),
        "DEF": ("DEF", "DEFs"),
        "DL": ("DL", "DLs"),
        "LB": ("LB", "LBs"),
        "DB": ("DB", "DBs"),
        "UNKNOWN": ("Unknown-position player", "Unknown-position players"),
    }
    singular, plural = labels.get(position, (position, f"{position}s"))
    return (singular, "is") if count == 1 else (plural, "are")


def _build_flexibility_note(
    conn: duckdb.DuckDBPyConnection, league_id: str, roster_id: int
) -> str | None:
    roster_row = conn.execute(
        """
        SELECT starters, players, reserve, taxi
        FROM rosters
        WHERE league_id = ? AND roster_id = ?
        LIMIT 1
        """,
        [league_id, roster_id],
    ).fetchone()
    if roster_row is None:
        return None

    starters = [str(player_id) for player_id in _loads(roster_row[0], [])]
    players = [str(player_id) for player_id in _loads(roster_row[1], [])]
    reserve = {str(player_id) for player_id in _loads(roster_row[2], [])}
    taxi = {str(player_id) for player_id in _loads(roster_row[3], [])}
    excluded = set(starters) | reserve | taxi
    roster = starters + [player_id for player_id in players if player_id not in excluded]
    if not roster:
        return None

    position_rows = conn.execute(
        """
        SELECT player_id, COALESCE(position, 'UNKNOWN')
        FROM players
        WHERE player_id IN (SELECT UNNEST(?))
        """,
        [roster],
    ).fetchall()
    player_positions = {str(row[0]): str(row[1] or "UNKNOWN") for row in position_rows}

    counts: dict[str, int] = {}
    for player_id in roster:
        position = player_positions.get(player_id, "UNKNOWN")
        counts[position] = counts.get(position, 0) + 1

    dominant_position, dominant_count = max(
        counts.items(), key=lambda item: (item[1], item[0])
    )
    label, verb = _position_group_phrase(dominant_position, dominant_count)
    share = round((dominant_count / len(roster)) * 100)
    return f"{label} {verb} {dominant_count} of {len(roster)} starters/bench players ({share}%)."


def _derive_primary_weakness(
    scorecard_row: tuple[Any, ...] | None,
    *,
    conn: duckdb.DuckDBPyConnection | None = None,
    league_id: str | None = None,
    roster_id: int | None = None,
) -> str:
    if scorecard_row is None:
        return "Run Phase 2 intelligence to surface the primary roster weakness."
    scorecard = {
        field: float(value)
        for field, value in zip(SCORECARD_FIELDS, scorecard_row, strict=False)
    }
    weakest = min(
        scorecard.items(),
        key=lambda item: (
            1.0 - item[1] if item[0] in HIGHER_IS_WORSE_FIELDS else item[1]
        ),
    )[0]
    if (
        weakest == "flexibility"
        and conn is not None
        and league_id is not None
        and roster_id is not None
    ):
        flexibility_note = _build_flexibility_note(conn, league_id, roster_id)
        if flexibility_note is not None:
            return flexibility_note
    return WEAKNESS_LABELS.get(
        weakest, "This roster needs more clarity before surfacing a weakness."
    )


def _portfolio_owner_selection(
    conn: duckdb.DuckDBPyConnection,
) -> tuple[str | None, bool]:
    settings = get_settings()

    if settings.PORTFOLIO_OWNER_ID:
        row = conn.execute(
            """
            SELECT owner_id
            FROM rosters
            WHERE owner_id = ?
            LIMIT 1
            """,
            [settings.PORTFOLIO_OWNER_ID],
        ).fetchone()
        return (str(row[0]), False) if row else (None, True)

    if settings.PORTFOLIO_OWNER_DISPLAY_NAME:
        row = conn.execute(
            """
            SELECT owner_id, COUNT(DISTINCT league_id) AS league_count
            FROM rosters
            WHERE owner_id IS NOT NULL
              AND owner_display_name IS NOT NULL
              AND lower(owner_display_name) = lower(?)
            GROUP BY owner_id
            ORDER BY league_count DESC, owner_id ASC
            LIMIT 1
            """,
            [settings.PORTFOLIO_OWNER_DISPLAY_NAME],
        ).fetchone()
        return (str(row[0]), False) if row else (None, True)

    row = conn.execute(
        """
        SELECT owner_id, COUNT(DISTINCT league_id) AS league_count
        FROM rosters
        WHERE owner_id IS NOT NULL
        GROUP BY owner_id
        ORDER BY league_count DESC, owner_id ASC
        LIMIT 1
        """
    ).fetchone()
    return (str(row[0]), True) if row else (None, True)


def _user_roster_for_league(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    portfolio_owner_id: str | None,
    *,
    allow_fallback: bool,
) -> tuple[int | None, str | None]:
    if portfolio_owner_id is not None:
        owner_row = conn.execute(
            """
            SELECT roster_id, owner_id
            FROM rosters
            WHERE league_id = ? AND owner_id = ?
            ORDER BY roster_id
            LIMIT 1
            """,
            [league_id, portfolio_owner_id],
        ).fetchone()
        if owner_row is not None:
            return int(owner_row[0]), owner_row[1]

    if not allow_fallback:
        return None, None

    fallback = conn.execute(
        """
        SELECT roster_id, owner_id
        FROM rosters
        WHERE league_id = ?
        ORDER BY roster_id
        LIMIT 1
        """,
        [league_id],
    ).fetchone()
    if fallback is None:
        return None, None
    return int(fallback[0]), fallback[1]


def _requested_roster_for_league(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    requested_roster_id: int | None,
    portfolio_owner_id: str | None,
    *,
    allow_fallback: bool,
) -> tuple[int | None, str | None, str | None]:
    if requested_roster_id is not None and requested_roster_id > 0:
        requested = conn.execute(
            """
            SELECT roster_id, owner_id, owner_display_name
            FROM rosters
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, requested_roster_id],
        ).fetchone()
        if requested is not None:
            return (
                int(requested[0]),
                str(requested[1]) if requested[1] is not None else None,
                str(requested[2]) if requested[2] is not None else None,
            )

    roster_id, owner_id = _user_roster_for_league(
        conn,
        league_id,
        portfolio_owner_id,
        allow_fallback=allow_fallback,
    )
    if roster_id is None:
        return None, None, None

    row = conn.execute(
        """
        SELECT owner_display_name
        FROM rosters
        WHERE league_id = ? AND roster_id = ?
        LIMIT 1
        """,
        [league_id, roster_id],
    ).fetchone()
    return (
        roster_id,
        str(owner_id) if owner_id is not None else None,
        str(row[0]) if row and row[0] is not None else None,
    )


def _latest_snapshot_at(conn: duckdb.DuckDBPyConnection, league_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT CAST(MAX(snapshot_at) AS VARCHAR)
        FROM league_snapshots
        WHERE league_id = ?
        """,
        [league_id],
    ).fetchone()
    return str(row[0]) if row and row[0] is not None else None


def _latest_ingest_at(conn: duckdb.DuckDBPyConnection, league_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT CAST(MAX(completed_at) AS VARCHAR)
        FROM ingest_runs
        WHERE league_id = ? AND status = 'complete'
        """,
        [league_id],
    ).fetchone()
    return str(row[0]) if row and row[0] is not None else None


def _recent_cutoff(days: int) -> datetime:
    return datetime.now() - timedelta(days=days)


def _tradeable_rosters(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    user_roster_id: int | None,
    *,
    days: int,
) -> set[int]:
    rows = conn.execute(
        """
        SELECT roster_ids
        FROM transactions
        WHERE league_id = ? AND type = 'trade' AND status = 'complete' AND created_at >= ?
        """,
        [league_id, _recent_cutoff(days)],
    ).fetchall()
    roster_ids: set[int] = set()
    for row in rows:
        for value in _loads(row[0], []):
            roster_id = int(value)
            if user_roster_id is not None and roster_id == user_roster_id:
                continue
            roster_ids.add(roster_id)
    return roster_ids


def _build_exploit_windows(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    user_roster_id: int | None,
) -> list[ExploitWindowManager]:
    roster_rows = conn.execute(
        """
        SELECT roster_id, owner_id, owner_display_name
        FROM rosters
        WHERE league_id = ?
        ORDER BY roster_id
        """,
        [league_id],
    ).fetchall()
    owner_names = {
        int(row[0]): str(row[2] or row[1] or f"Roster {int(row[0])}") for row in roster_rows
    }
    direction_map = {
        int(row[0]): str(row[1])
        for row in conn.execute(
            """
            SELECT roster_id, primary_label
            FROM team_directions
            WHERE league_id = ?
            """,
            [league_id],
        ).fetchall()
    }
    player_positions = {
        str(row[0]): str(row[1] or "UNKNOWN")
        for row in conn.execute(
            "SELECT player_id, position FROM players"
        ).fetchall()
    }

    transaction_rows = conn.execute(
        """
        SELECT roster_ids, adds, drops, draft_picks
        FROM transactions
        WHERE league_id = ? AND type = 'trade' AND status = 'complete' AND created_at >= ?
        ORDER BY created_at DESC NULLS LAST
        """,
        [league_id, _recent_cutoff(RECENT_EXPLOIT_WINDOW_DAYS)],
    ).fetchall()
    trade_counts: dict[int, int] = {}
    pick_counts: dict[int, int] = {}
    position_receipts: dict[int, dict[str, int]] = {}
    for row in transaction_rows:
        roster_ids = [int(value) for value in _loads(row[0], [])]
        adds = _loads(row[1], {})
        picks = _loads(row[3], [])
        for roster_id in roster_ids:
            if user_roster_id is not None and roster_id == user_roster_id:
                continue
            trade_counts[roster_id] = trade_counts.get(roster_id, 0) + 1
            position_receipts.setdefault(roster_id, {})
        for player_id, target_roster in adds.items():
            roster_id = int(target_roster)
            if user_roster_id is not None and roster_id == user_roster_id:
                continue
            position = player_positions.get(str(player_id), "UNKNOWN")
            bucket = position_receipts.setdefault(roster_id, {})
            bucket[position] = bucket.get(position, 0) + 1
        for pick in picks:
            owner_id = pick.get("owner_id")
            previous_owner_id = pick.get("previous_owner_id")
            for raw_roster in (owner_id, previous_owner_id):
                if raw_roster is None:
                    continue
                roster_id = int(raw_roster)
                if user_roster_id is not None and roster_id == user_roster_id:
                    continue
                pick_counts[roster_id] = pick_counts.get(roster_id, 0) + 1

    windows: list[ExploitWindowManager] = []
    roster_ids = sorted(set(owner_names) | set(trade_counts) | set(pick_counts))
    for roster_id in roster_ids:
        if user_roster_id is not None and roster_id == user_roster_id:
            continue
        triggers: list[ExploitTrigger] = []
        trade_count = trade_counts.get(roster_id, 0)
        if trade_count >= 2:
            triggers.append(
                ExploitTrigger(
                    type="recent_activity",
                    description=f"{trade_count} recent trades suggest this manager is open to deals.",
                    suggested_action="Lead with a concise offer while the manager is actively moving pieces.",
                )
            )
        pick_count = pick_counts.get(roster_id, 0)
        if pick_count >= 1:
            triggers.append(
                ExploitTrigger(
                    type="pick_activity",
                    description=(
                        f"{pick_count} recent pick swaps suggest this manager is willing "
                        "to rebalance future assets."
                    ),
                    suggested_action="Test veteran-for-pick or pick-for-insulation frameworks first.",
                )
            )
        position_counts = position_receipts.get(roster_id, {})
        if position_counts:
            chased_position, chase_count = max(
                position_counts.items(), key=lambda item: item[1]
            )
            if chased_position != "UNKNOWN" and chase_count >= 2:
                triggers.append(
                    ExploitTrigger(
                        type="position_chase",
                        description=f"They have repeatedly added {chased_position} assets in recent deals.",
                        suggested_action=f"Offer {chased_position} depth at a premium while demand is visible.",
                    )
                )
        direction_label = direction_map.get(roster_id)
        if (
            direction_label in REBUILD_DIRECTION_LABELS
            and trade_count >= 2
            and pick_counts.get(roster_id, 0) == 0
        ):
            triggers.append(
                ExploitTrigger(
                    type="direction_noise",
                    description=f"Recent trade volume does not appear to reinforce a {direction_label.replace('_', ' ')} path.",
                    suggested_action="Float flexible two-for-one offers that simplify their roster decisions.",
                )
            )

        if not triggers:
            continue
        windows.append(
            ExploitWindowManager(
                roster_id=roster_id,
                manager_name=owner_names.get(roster_id),
                trigger_count=len(triggers),
                is_high_opportunity=trade_count >= 7
                or (
                    len(triggers) >= 3
                    and trade_count >= 5
                    and pick_count >= 10
                ),
                triggers=triggers,
            )
        )

    return sorted(
        windows,
        key=lambda window: (window.trigger_count, window.is_high_opportunity, window.roster_id),
        reverse=True,
    )


def _top_exploit_window(
    conn: duckdb.DuckDBPyConnection, league_id: str, user_roster_id: int | None
) -> str | None:
    windows = _build_exploit_windows(conn, league_id, user_roster_id)
    if not windows:
        return None
    top = windows[0]
    manager_name = top.manager_name or f"Roster {top.roster_id}"
    return f"{manager_name}: {top.trigger_count} live triggers"


def _snapshot_pair_payloads(
    conn: duckdb.DuckDBPyConnection, league_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT payload_json
        FROM league_snapshots
        WHERE league_id = ?
        ORDER BY snapshot_at DESC, id DESC
        LIMIT 2
        """,
        [league_id],
    ).fetchall()
    payloads = [_loads(row[0], {}) for row in rows]
    latest = payloads[0] if payloads else {}
    previous = payloads[1] if len(payloads) > 1 else {}
    return latest, previous


def _build_risers_fallers(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    user_roster_id: int | None,
) -> tuple[list[RiserFallerEntry], list[RiserFallerEntry]]:
    latest_payload, previous_payload = _snapshot_pair_payloads(conn, league_id)
    latest_state = latest_payload.get("state", {}) if isinstance(latest_payload, dict) else {}
    previous_state = previous_payload.get("state", {}) if isinstance(previous_payload, dict) else {}
    if not latest_state or not previous_state:
        return [], []

    actionable_rosters = {
        roster_id
        for roster_id in _tradeable_rosters(
            conn,
            league_id,
            user_roster_id,
            days=RECENT_TRADEABILITY_DAYS,
        )
    }
    previous_market: dict[tuple[int, str], float] = {}
    for roster in previous_state.get("rosters", []):
        roster_id = int(roster.get("roster_id", 0))
        for player in roster.get("player_values", []):
            lens_market = player.get("lens_market")
            if lens_market is None:
                continue
            previous_market[(roster_id, str(player.get("player_id")))] = float(lens_market)

    deltas: list[tuple[str, float]] = []
    for roster in latest_state.get("rosters", []):
        roster_id = int(roster.get("roster_id", 0))
        if user_roster_id is not None and roster_id == user_roster_id:
            continue
        if roster_id not in actionable_rosters:
            continue
        for player in roster.get("player_values", []):
            player_id = str(player.get("player_id"))
            current_value = player.get("lens_market")
            previous_value = previous_market.get((roster_id, player_id))
            if current_value is None or previous_value is None:
                continue
            delta = round(float(current_value) - previous_value, 2)
            if abs(delta) < 0.01:
                continue
            deltas.append((str(player.get("player_name") or player_id), delta))

    risers = [
        RiserFallerEntry(
            player_name=name,
            delta=delta,
            reason="Market value rose versus the previous ingest snapshot.",
        )
        for name, delta in sorted(deltas, key=lambda item: item[1], reverse=True)[:5]
        if delta > 0
    ]
    fallers = [
        RiserFallerEntry(
            player_name=name,
            delta=delta,
            reason="Market value fell versus the previous ingest snapshot.",
        )
        for name, delta in sorted(deltas, key=lambda item: item[1])[:5]
        if delta < 0
    ]
    return risers, fallers


@router.get("/summary", response_model=list[DashboardLeagueSummary])
def get_dashboard_summary(
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> list[DashboardLeagueSummary]:
    leagues = conn.execute(
        "SELECT league_id, name FROM leagues ORDER BY name, league_id"
    ).fetchall()
    portfolio_owner, allow_fallback = _portfolio_owner_selection(conn)
    summaries: list[DashboardLeagueSummary] = []
    for league_id, league_name in leagues:
        roster_id, _ = _user_roster_for_league(
            conn,
            str(league_id),
            portfolio_owner,
            allow_fallback=allow_fallback,
        )
        direction_label = "Analysis not yet run"
        confidence_band: Literal["High", "Medium", "Low", "--"] = "--"
        direction_read: DirectionReadBand = "--"
        direction_alternates: list[str] = []
        direction_note: str | None = None
        summary_signal = "Run Phase 2 intelligence to surface your top edge."
        primary_weakness = "Run Phase 2 intelligence to surface the primary roster weakness."
        if roster_id is not None:
            direction_row = conn.execute(
                """
                SELECT primary_label, confidence, alternates_json
                FROM team_directions
                WHERE league_id = ? AND roster_id = ?
                """,
                [league_id, roster_id],
            ).fetchone()
            if direction_row is not None:
                direction_label = str(direction_row[0])
                confidence = float(direction_row[1])
                alternates = _loads(direction_row[2], [])
                confidence_band = _band(confidence)
                direction_read = _direction_read(confidence, alternates)
                direction_alternates = _alternate_labels(alternates)
                direction_note = _direction_note(
                    direction_label,
                    direction_read,
                    alternates,
                )
            scorecard_row = conn.execute(
                """
                SELECT win_now, future_value, depth, pick_capital, flexibility,
                       fragility, age_risk, liquidity, positional_insulation
                FROM team_scorecards
                WHERE league_id = ? AND roster_id = ?
                """,
                [league_id, roster_id],
            ).fetchone()
            summary_signal = _derive_summary_signal(
                conn,
                str(league_id),
                roster_id,
                scorecard_row,
            )
            primary_weakness = _derive_primary_weakness(
                scorecard_row,
                conn=conn,
                league_id=str(league_id),
                roster_id=roster_id,
            )

        summaries.append(
            DashboardLeagueSummary(
                league_id=str(league_id),
                league_name=str(league_name),
                user_roster_id=roster_id,
                direction_label=direction_label,
                confidence_band=confidence_band,
                direction_read=direction_read,
                direction_alternates=direction_alternates,
                direction_note=direction_note,
                summary_signal=summary_signal,
                primary_weakness=primary_weakness,
                top_exploit_window=_top_exploit_window(conn, str(league_id), roster_id),
                last_snapshot_at=_latest_snapshot_at(conn, str(league_id)),
                last_ingest_at=_latest_ingest_at(conn, str(league_id)),
            )
        )
    return summaries


@router.get("/league/{league_id}/rosters", response_model=list[LeagueRosterOption])
def get_league_rosters(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> list[LeagueRosterOption]:
    rows = conn.execute(
        """
        SELECT r.roster_id, r.owner_id, r.owner_display_name,
               COALESCE(s.wins, 0), COALESCE(s.losses, 0), COALESCE(s.ties, 0),
               COALESCE(s.fpts, 0.0)
        FROM rosters r
        LEFT JOIN standings s
          ON s.league_id = r.league_id
         AND s.roster_id = r.roster_id
        WHERE r.league_id = ?
        ORDER BY r.roster_id
        """,
        [league_id],
    ).fetchall()

    return [
        LeagueRosterOption(
            roster_id=int(row[0]),
            owner_id=str(row[1]) if row[1] is not None else None,
            owner_display_name=str(row[2]) if row[2] is not None else None,
            wins=int(row[3] or 0),
            losses=int(row[4] or 0),
            ties=int(row[5] or 0),
            points_for=float(row[6] or 0.0),
        )
        for row in rows
    ]


def _player_rank_score(row: tuple[Any, ...]) -> float:
    market = float(row[8]) if row[8] is not None else 0.0
    production = float(row[9]) if row[9] is not None else 0.0
    insulation = float(row[10]) if row[10] is not None else 0.0
    direction = float(row[11]) if row[11] is not None else 0.0
    fantasycalc_value = float(row[13]) if row[13] is not None else 0.0
    normalized_market_value = min(fantasycalc_value / 10_000.0, 1.0)
    return round(
        (market * 0.40)
        + (insulation * 0.25)
        + (production * 0.20)
        + (direction * 0.10)
        + (normalized_market_value * 0.05),
        4,
    )


@router.get("/league/{league_id}/player-rankings", response_model=PlayerRankingsResponse)
def get_league_player_rankings(
    league_id: str,
    roster_id: int | None = None,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> PlayerRankingsResponse:
    league_row = conn.execute(
        "SELECT league_id FROM leagues WHERE league_id = ?",
        [league_id],
    ).fetchone()
    if league_row is None:
        raise HTTPException(status_code=404, detail="League not found")

    portfolio_owner, allow_fallback = _portfolio_owner_selection(conn)
    user_roster_id, _, _ = _requested_roster_for_league(
        conn,
        league_id,
        roster_id,
        portfolio_owner,
        allow_fallback=allow_fallback,
    )
    rows = conn.execute(
        """
        SELECT
            pv.player_id,
            COALESCE(p.full_name, pv.player_id) AS player_name,
            COALESCE(p.position, 'UNKNOWN') AS position,
            p.team,
            p.age,
            pv.roster_id,
            COALESCE(r.owner_display_name, r.owner_id, 'Roster ' || CAST(pv.roster_id AS VARCHAR)) AS owner_name,
            pv.computed_at,
            pv.lens_market,
            pv.lens_production,
            pv.lens_insulation,
            pv.lens_direction,
            mv.fantasycalc_rank,
            mv.fantasycalc_value,
            mv.fantasycalc_trend30
        FROM player_values pv
        LEFT JOIN players p
          ON p.player_id = pv.player_id
        LEFT JOIN rosters r
          ON r.league_id = pv.league_id
         AND r.roster_id = pv.roster_id
        LEFT JOIN market_values mv
          ON mv.player_id = pv.player_id
        WHERE pv.league_id = ?
        ORDER BY
            COALESCE(mv.fantasycalc_rank, 9999) ASC,
            COALESCE(pv.lens_market, 0) DESC,
            COALESCE(pv.lens_insulation, 0) DESC,
            COALESCE(pv.lens_production, 0) DESC,
            player_name ASC
        """,
        [league_id],
    ).fetchall()

    scored_rows = [(row, _player_rank_score(row)) for row in rows]
    scored_rows.sort(
        key=lambda item: (
            int(item[0][12]) if item[0][12] is not None else 9999,
            -item[1],
            str(item[0][1]),
        )
    )
    position_counts: dict[str, int] = {}
    rankings: list[PlayerRankingEntry] = []
    for index, (row, score) in enumerate(scored_rows, start=1):
        position = str(row[2] or "UNKNOWN")
        position_counts[position] = position_counts.get(position, 0) + 1
        rankings.append(
            PlayerRankingEntry(
                player_id=str(row[0]),
                player_name=str(row[1]),
                position=position,
                team=str(row[3]) if row[3] is not None else None,
                age=int(row[4]) if row[4] is not None else None,
                roster_id=int(row[5]),
                owner_name=str(row[6]),
                is_user_roster=user_roster_id is not None and int(row[5]) == user_roster_id,
                rank=index,
                position_rank=position_counts[position],
                tier=max(1, math.ceil(index / 12)),
                rank_score=score,
                lens_market=float(row[8]) if row[8] is not None else None,
                lens_production=float(row[9]) if row[9] is not None else None,
                lens_insulation=float(row[10]) if row[10] is not None else None,
                lens_direction=float(row[11]) if row[11] is not None else None,
                fantasycalc_rank=int(row[12]) if row[12] is not None else None,
                fantasycalc_value=float(row[13]) if row[13] is not None else None,
                trend_30day=float(row[14]) if row[14] is not None else None,
            )
        )

    return PlayerRankingsResponse(league_id=league_id, rankings=rankings)


@router.get("/league/{league_id}", response_model=LeagueDetailResponse)
def get_league_detail(
    league_id: str,
    roster_id: int | None = None,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> LeagueDetailResponse:
    league_row = conn.execute(
        "SELECT name FROM leagues WHERE league_id = ?",
        [league_id],
    ).fetchone()
    if league_row is None:
        raise HTTPException(status_code=404, detail="League not found")

    portfolio_owner, allow_fallback = _portfolio_owner_selection(conn)
    roster_id, owner_id, owner_display_name = _requested_roster_for_league(
        conn,
        league_id,
        roster_id,
        portfolio_owner,
        allow_fallback=allow_fallback,
    )
    direction_label = "Analysis not yet run"
    confidence_band: Literal["High", "Medium", "Low", "--"] = "--"
    direction_read: DirectionReadBand = "--"
    direction_alternates: list[str] = []
    direction_note: str | None = None
    direction_reasoning: str | None = None
    primary_weakness = "Run Phase 2 intelligence to surface the primary roster weakness."
    user_roster_player_ids: list[str] = []
    scorecard_row: tuple[Any, ...] | None = None

    if roster_id is not None:
        direction_row = conn.execute(
            """
            SELECT primary_label, confidence, reasoning, alternates_json
            FROM team_directions
            WHERE league_id = ? AND roster_id = ?
            """,
            [league_id, roster_id],
        ).fetchone()
        if direction_row is not None:
            direction_label = str(direction_row[0])
            confidence = float(direction_row[1])
            direction_reasoning = (
                str(direction_row[2]) if direction_row[2] is not None else None
            )
            alternates = _loads(direction_row[3], [])
            confidence_band = _band(confidence)
            direction_read = _direction_read(confidence, alternates)
            direction_alternates = _alternate_labels(alternates)
            direction_note = _direction_note(
                direction_label,
                direction_read,
                alternates,
            )
        scorecard_row = conn.execute(
            """
            SELECT win_now, future_value, depth, pick_capital, flexibility,
                   fragility, age_risk, liquidity, positional_insulation
            FROM team_scorecards
            WHERE league_id = ? AND roster_id = ?
            """,
            [league_id, roster_id],
        ).fetchone()
        primary_weakness = _derive_primary_weakness(
            scorecard_row,
            conn=conn,
            league_id=league_id,
            roster_id=roster_id,
        )
        roster_players_row = conn.execute(
            """
            SELECT players
            FROM rosters
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if roster_players_row is not None:
            user_roster_player_ids = [
                str(player_id)
                for player_id in _loads(roster_players_row[0], [])
                if player_id not in (None, "", 0, "0")
            ]

    risers, fallers = _build_risers_fallers(conn, league_id, roster_id)
    exploit_windows = _build_exploit_windows(conn, league_id, roster_id)
    return LeagueDetailResponse(
        league_id=league_id,
        league_name=str(league_row[0]),
        user_roster_id=roster_id,
        user_roster_name=owner_display_name
        or (f"Roster {roster_id}" if roster_id is not None else None),
        user_owner_id=owner_id,
        user_roster_player_ids=user_roster_player_ids,
        direction_label=direction_label,
        confidence_band=confidence_band,
        direction_read=direction_read,
        direction_alternates=direction_alternates,
        direction_note=direction_note,
        direction_reasoning=direction_reasoning,
        direction_fit_flags=_direction_fit_flags(direction_label, scorecard_row),
        primary_weakness=primary_weakness,
        risers=risers,
        fallers=fallers,
        exploit_windows=exploit_windows,
        last_snapshot_at=_latest_snapshot_at(conn, league_id),
        last_ingest_at=_latest_ingest_at(conn, league_id),
        recommendation_context=_build_recommendation_context(conn, league_id),
        competitive_landscape=_build_competitive_landscape(conn, league_id, roster_id),
    )

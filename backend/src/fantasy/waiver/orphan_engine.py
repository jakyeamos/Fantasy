from __future__ import annotations

import json
from datetime import datetime, timezone
from statistics import median
from typing import Any

import duckdb

from fantasy.waiver.constants import (
    ORPHAN_BALANCED_MAX,
    ORPHAN_DISTRESSED_MAX,
    ORPHAN_REBUILDER_MAX,
    ORPHAN_WEIGHT_AGE_CURVE,
    ORPHAN_WEIGHT_DEAD_SPOTS,
    ORPHAN_WEIGHT_LIQUIDATION,
    ORPHAN_WEIGHT_LINEUP,
    ORPHAN_WEIGHT_PICK_CAPITAL,
    URGENCY_ORDER,
)
from fantasy.waiver.models import ActionPlan, ActionPlanItem, OrphanIntake, OrphanIntakeDimension
from fantasy.waiver.waiver_engine import WaiverEngine


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def compute_orphan_composite(
    age_curve_score: float,
    pick_capital_score: float,
    dead_spots_score: float,
    lineup_viability_score: float,
    liquidation_score: float,
) -> float:
    raw = (
        age_curve_score * ORPHAN_WEIGHT_AGE_CURVE
        + pick_capital_score * ORPHAN_WEIGHT_PICK_CAPITAL
        + dead_spots_score * ORPHAN_WEIGHT_DEAD_SPOTS
        + lineup_viability_score * ORPHAN_WEIGHT_LINEUP
        + liquidation_score * ORPHAN_WEIGHT_LIQUIDATION
    )
    return max(0.0, min(100.0, raw))


def get_composite_label(composite: float) -> str:
    if composite <= ORPHAN_DISTRESSED_MAX:
        return "Distressed"
    if composite <= ORPHAN_REBUILDER_MAX:
        return "Rebuilder"
    if composite <= ORPHAN_BALANCED_MAX:
        return "Balanced"
    return "Ready to Compete"


class OrphanEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn
        self._waiver_engine = WaiverEngine(conn)

    def _roster_player_ids(self, league_id: str, roster_id: int) -> list[str]:
        row = self._conn.execute(
            """
            SELECT players
            FROM rosters
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        return [str(player_id) for player_id in _loads(row[0], [])] if row else []

    def _age_curve_score(self, league_id: str, roster_id: int, player_ids: list[str]) -> float:
        rows = self._conn.execute(
            """
            SELECT comp_age_curve
            FROM player_values
            WHERE league_id = ? AND roster_id = ?
            """,
            [league_id, roster_id],
        ).fetchall()
        values = [float(row[0]) for row in rows if row[0] is not None]
        if values:
            hits = sum(1 for value in values if value >= 50.0)
            return round((hits / len(values)) * 100.0, 2)
        if not player_ids:
            return 0.0
        age_rows = self._conn.execute(
            """
            SELECT age
            FROM players
            WHERE player_id IN (SELECT UNNEST(?))
            """,
            [player_ids],
        ).fetchall()
        ages = [int(row[0]) for row in age_rows if row[0] is not None]
        if not ages:
            return 0.0
        hits = sum(1 for age in ages if age <= 25)
        return round((hits / len(ages)) * 100.0, 2)

    def _pick_capital_score(self, league_id: str, roster_id: int) -> float:
        team_rows = self._conn.execute(
            """
            SELECT COALESCE(SUM(demand_adjusted_value), 0.0)
            FROM pick_values
            WHERE league_id = ? AND pick_owner_roster_id = ?
            """,
            [league_id, roster_id],
        ).fetchone()
        team_total = float(team_rows[0] or 0.0) if team_rows else 0.0
        league_rows = self._conn.execute(
            """
            SELECT pick_owner_roster_id, COALESCE(SUM(demand_adjusted_value), 0.0) AS total_value
            FROM pick_values
            WHERE league_id = ?
            GROUP BY pick_owner_roster_id
            """,
            [league_id],
        ).fetchall()
        if not league_rows:
            return 0.0
        league_median = median(float(row[1] or 0.0) for row in league_rows) or 1.0
        return round(max(0.0, min(100.0, (team_total / max(league_median, 1.0)) * 100.0)), 2)

    def _dead_spots_score(self, league_id: str, roster_id: int, roster_size: int) -> tuple[float, list[dict[str, Any]]]:
        row = self._conn.execute(
            """
            SELECT suggestions_json
            FROM hygiene_suggestions
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        suggestions = _loads(row[0], []) if row else []
        cut_suggestions = [item for item in suggestions if item.get("action_type") == "cut"]
        cut_count = len(cut_suggestions)
        score = max(0.0, 100.0 - ((cut_count / max(1, roster_size)) * 100.0))
        return round(score, 2), cut_suggestions

    def _lineup_viability_score(self, league_id: str, roster_id: int) -> float:
        team_row = self._conn.execute(
            """
            SELECT total_lineup_score
            FROM lineup_scores
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if team_row is None or team_row[0] is None:
            return 0.0
        team_total = float(team_row[0])
        league_rows = self._conn.execute(
            """
            SELECT total_lineup_score
            FROM lineup_scores
            WHERE league_id = ?
            """,
            [league_id],
        ).fetchall()
        league_median = median(float(row[0]) for row in league_rows if row[0] is not None) if league_rows else 1.0
        return round(max(0.0, min(100.0, (team_total / max(league_median, 1.0)) * 100.0)), 2)

    def _liquidation_score(self, league_id: str, roster_id: int, roster_size: int) -> float:
        row = self._conn.execute(
            """
            SELECT COUNT(*)
            FROM player_values
            WHERE league_id = ? AND roster_id = ? AND COALESCE(lens_market, 0) > 60
            """,
            [league_id, roster_id],
        ).fetchone()
        liquid_count = int(row[0] or 0) if row else 0
        score = min(100.0, (liquid_count / max(1, roster_size)) * 200.0)
        return round(score, 2)

    def _dimension(self, score: float, *, high: str, mid: str, low: str, summary_high: str, summary_low: str) -> OrphanIntakeDimension:
        if score >= 70:
            return OrphanIntakeDimension(score=score, label=high, summary=summary_high)
        if score >= 45:
            return OrphanIntakeDimension(
                score=score,
                label=mid,
                summary="This area is workable but still needs active management.",
            )
        return OrphanIntakeDimension(score=score, label=low, summary=summary_low)

    def _approved_moves(self, league_id: str, roster_id: int) -> list[str]:
        row = self._conn.execute(
            """
            SELECT approved_moves
            FROM team_directions
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        return [str(item) for item in _loads(row[0], [])] if row else []

    def compute_intake(self, league_id: str, roster_id: int) -> OrphanIntake:
        player_ids = self._roster_player_ids(league_id, roster_id)
        roster_size = len(player_ids)
        age_curve_score = self._age_curve_score(league_id, roster_id, player_ids)
        pick_capital_score = self._pick_capital_score(league_id, roster_id)
        dead_spots_score, _ = self._dead_spots_score(league_id, roster_id, roster_size)
        lineup_viability_score = self._lineup_viability_score(league_id, roster_id)
        liquidation_score = self._liquidation_score(league_id, roster_id, roster_size)
        composite_score = compute_orphan_composite(
            age_curve_score,
            pick_capital_score,
            dead_spots_score,
            lineup_viability_score,
            liquidation_score,
        )
        composite_label = get_composite_label(composite_score)

        return OrphanIntake(
            league_id=league_id,
            roster_id=roster_id,
            composite_score=composite_score,
            composite_label=composite_label,  # type: ignore[arg-type]
            age_curve=self._dimension(
                age_curve_score,
                high="Young core",
                mid="Mixed timeline",
                low="Aging curve",
                summary_high="The roster still has runway. You can afford to be patient.",
                summary_low="Too much of the roster is already on the wrong side of the curve.",
            ),
            pick_capital=self._dimension(
                pick_capital_score,
                high="Armed with picks",
                mid="Average pick bank",
                low="Pick deficit",
                summary_high="Future picks give this team multiple exits and reroll paths.",
                summary_low="Pick capital trails the room. Acquiring first-round equity should be a priority.",
            ),
            dead_spots=self._dimension(
                dead_spots_score,
                high="Flexible bench",
                mid="Manageable clutter",
                low="Dead weight",
                summary_high="The bench can turn over quickly when opportunities show up.",
                summary_low="Too many roster spots are blocked by low-utility players.",
            ),
            lineup_viability=self._dimension(
                lineup_viability_score,
                high="Playable today",
                mid="Thin but viable",
                low="Weekly liability",
                summary_high="The current lineup can survive while you work the medium-term plan.",
                summary_low="Weekly starter quality is lagging behind league median.",
            ),
            liquidation_options=self._dimension(
                liquidation_score,
                high="Liquid market",
                mid="Some movable pieces",
                low="Few sellable assets",
                summary_high="You have credible chips to reroute into picks or insulation.",
                summary_low="There are not many liquid veterans to sell, so every move matters.",
            ),
            computed_at=datetime.now(timezone.utc).isoformat(),
        )

    def generate_action_plan(
        self,
        league_id: str,
        roster_id: int,
        plan_type: str = "orphan_intake",
    ) -> ActionPlan:
        intake = self.compute_intake(league_id, roster_id)
        plan_type_value = (
            plan_type
            if plan_type in {"orphan_intake", "startup", "new_connection"}
            else "orphan_intake"
        )
        items: list[ActionPlanItem] = []

        waiver_result = self._waiver_engine.compute_recommendations(league_id, roster_id)
        for recommendation in waiver_result.recommendations[:3]:
            items.append(
                ActionPlanItem(
                    priority_rank=0,
                    category="add",
                    headline=f"Add {recommendation.player_name}",
                    rationale=recommendation.rationale,
                    urgency="this_week",
                    target_entity_type="player",
                    target_entity_ids=[recommendation.player_id],
                    confidence_label="HIGH" if recommendation.urgency == "High" else "MEDIUM",
                )
            )

        _, cut_suggestions = self._dead_spots_score(
            league_id,
            roster_id,
            len(self._roster_player_ids(league_id, roster_id)),
        )
        for suggestion in cut_suggestions[:3]:
            names = [str(name) for name in suggestion.get("primary_player_names", [])]
            ids = [str(item) for item in suggestion.get("primary_player_ids", [])]
            items.append(
                ActionPlanItem(
                    priority_rank=0,
                    category="drop",
                    headline=f"Drop {', '.join(names) or 'dead-weight depth'}",
                    rationale=str(suggestion.get("reasoning") or "Free the roster spot for usable depth."),
                    urgency="this_week",
                    target_entity_type="player",
                    target_entity_ids=ids,
                    confidence_label="MEDIUM",
                )
            )

        for move in self._approved_moves(league_id, roster_id)[:2]:
            normalized = move.replace("_", " ")
            category = "trade" if any(token in move for token in ("trade", "sell", "buy", "acquire")) else "evaluate"
            items.append(
                ActionPlanItem(
                    priority_rank=0,
                    category=category,  # type: ignore[arg-type]
                    headline=normalized.title(),
                    rationale=f"The current roster direction explicitly supports: {normalized}.",
                    urgency="30_days",
                    target_entity_type="manager" if category == "trade" else "position",
                    target_entity_ids=[str(roster_id)] if category == "trade" else [],
                    confidence_label="MEDIUM",
                )
            )

        if intake.pick_capital.score < 50:
            items.append(
                ActionPlanItem(
                    priority_rank=0,
                    category="trade",
                    headline="Acquire a future first-round pick",
                    rationale="Your pick capital is below league median. Force at least one deal that adds future insulation.",
                    urgency="30_days",
                    target_entity_type="pick",
                    target_entity_ids=[],
                    confidence_label="HIGH",
                )
            )
        if intake.lineup_viability.score < 50:
            items.append(
                ActionPlanItem(
                    priority_rank=0,
                    category="evaluate",
                    headline="Audit weak starting slots",
                    rationale="Lineup viability is lagging. Decide which slots need short-term patching versus full rebuild treatment.",
                    urgency="30_days",
                    target_entity_type="position",
                    target_entity_ids=[],
                    confidence_label="MEDIUM",
                )
            )
        if intake.composite_label == "Distressed":
            if not any(item.category == "add" for item in items):
                items.append(
                    ActionPlanItem(
                        priority_rank=0,
                        category="add",
                        headline="Cycle the waiver wire for upside",
                        rationale="A distressed orphan needs immediate roster churn to uncover any usable value.",
                        urgency="this_week",
                        target_entity_type="position",
                        target_entity_ids=[],
                        confidence_label="HIGH",
                    )
                )
            if not any(item.category == "drop" for item in items):
                items.append(
                    ActionPlanItem(
                        priority_rank=0,
                        category="drop",
                        headline="Cut at least one blocked bench spot",
                        rationale="Make room for players you can actually evaluate over the next month.",
                        urgency="this_week",
                        target_entity_type="player",
                        target_entity_ids=[],
                        confidence_label="HIGH",
                    )
                )

        while len(items) < 5:
            items.append(
                ActionPlanItem(
                    priority_rank=0,
                    category="hold",
                    headline="Reassess the roster after the next ingest",
                    rationale="Use fresh data to confirm whether early moves changed the underlying trajectory.",
                    urgency="offseason" if len(items) >= 4 else "30_days",
                    target_entity_type="manager",
                    target_entity_ids=[str(roster_id)],
                    confidence_label="LOW",
                )
            )

        items.sort(key=lambda item: (URGENCY_ORDER[item.urgency], item.headline))
        renumbered = [
            item.model_copy(update={"priority_rank": index + 1})
            for index, item in enumerate(items)
        ]

        return ActionPlan(
            league_id=league_id,
            roster_id=roster_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            plan_type=plan_type_value,  # type: ignore[arg-type]
            items=renumbered,
            summary=(
                f"{intake.composite_label} roster. Start with immediate churn, then use the next "
                "30 days to improve insulation and pick leverage."
            ),
        )


__all__ = [
    "OrphanEngine",
    "compute_orphan_composite",
    "get_composite_label",
]

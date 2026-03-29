from __future__ import annotations

import json
from typing import Any

import duckdb

from fantasy.waiver.models import (
    ActionPlan,
    OrphanIntake,
    StartupContext,
    WaiverRecommendationsResponse,
)


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


class WaiverRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def _next_id(self, table: str) -> int:
        row = self._conn.execute(
            f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}"
        ).fetchone()
        return int(row[0]) if row else 1

    def upsert_waiver_recommendations(self, result: WaiverRecommendationsResponse) -> None:
        existing = self._conn.execute(
            """
            SELECT id
            FROM waiver_recommendations
            WHERE league_id = ? AND roster_id = ?
            """,
            [result.league_id, result.roster_id],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id("waiver_recommendations")
        self._conn.execute(
            """
            INSERT INTO waiver_recommendations (
                id, league_id, roster_id, recommendations_json
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT (league_id, roster_id) DO UPDATE SET
                recommendations_json = EXCLUDED.recommendations_json,
                computed_at = now()
            """,
            [row_id, result.league_id, result.roster_id, result.model_dump_json()],
        )

    def get_waiver_recommendations(
        self, league_id: str, roster_id: int
    ) -> WaiverRecommendationsResponse | None:
        row = self._conn.execute(
            """
            SELECT recommendations_json
            FROM waiver_recommendations
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            return None
        return WaiverRecommendationsResponse.model_validate_json(str(row[0]))

    def upsert_startup_context(self, context: StartupContext) -> None:
        existing = self._conn.execute(
            """
            SELECT id
            FROM startup_contexts
            WHERE league_id = ?
            """,
            [context.league_id],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id("startup_contexts")
        self._conn.execute(
            """
            INSERT INTO startup_contexts (
                id, league_id, draft_status, build_template, context_json
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (league_id) DO UPDATE SET
                draft_status = EXCLUDED.draft_status,
                build_template = EXCLUDED.build_template,
                context_json = EXCLUDED.context_json,
                computed_at = now()
            """,
            [
                row_id,
                context.league_id,
                context.draft_status,
                context.build_template,
                context.model_dump_json(),
            ],
        )

    def get_startup_context(self, league_id: str) -> StartupContext | None:
        row = self._conn.execute(
            """
            SELECT context_json
            FROM startup_contexts
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        if row is None:
            return None
        return StartupContext.model_validate_json(str(row[0]))

    def upsert_orphan_intake(self, intake: OrphanIntake) -> None:
        existing = self._conn.execute(
            """
            SELECT id
            FROM orphan_intakes
            WHERE league_id = ? AND roster_id = ?
            """,
            [intake.league_id, intake.roster_id],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id("orphan_intakes")
        self._conn.execute(
            """
            INSERT INTO orphan_intakes (
                id, league_id, roster_id, age_curve_score, pick_capital_score,
                dead_spots_score, lineup_viability_score, liquidation_score,
                composite_score, intake_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (league_id, roster_id) DO UPDATE SET
                age_curve_score = EXCLUDED.age_curve_score,
                pick_capital_score = EXCLUDED.pick_capital_score,
                dead_spots_score = EXCLUDED.dead_spots_score,
                lineup_viability_score = EXCLUDED.lineup_viability_score,
                liquidation_score = EXCLUDED.liquidation_score,
                composite_score = EXCLUDED.composite_score,
                intake_json = EXCLUDED.intake_json,
                computed_at = now()
            """,
            [
                row_id,
                intake.league_id,
                intake.roster_id,
                intake.age_curve.score,
                intake.pick_capital.score,
                intake.dead_spots.score,
                intake.lineup_viability.score,
                intake.liquidation_options.score,
                intake.composite_score,
                intake.model_dump_json(),
            ],
        )

    def get_orphan_intake(self, league_id: str, roster_id: int) -> OrphanIntake | None:
        row = self._conn.execute(
            """
            SELECT intake_json
            FROM orphan_intakes
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            return None
        return OrphanIntake.model_validate_json(str(row[0]))

    def upsert_action_plan(self, plan: ActionPlan) -> None:
        existing = self._conn.execute(
            """
            SELECT id
            FROM action_plans
            WHERE league_id = ? AND roster_id = ?
            """,
            [plan.league_id, plan.roster_id],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id("action_plans")
        items_json = json.dumps(
            [item.model_dump() for item in plan.items],
            separators=(",", ":"),
        )
        self._conn.execute(
            """
            INSERT INTO action_plans (
                id, league_id, roster_id, plan_type, items_json, summary
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (league_id, roster_id) DO UPDATE SET
                plan_type = EXCLUDED.plan_type,
                items_json = EXCLUDED.items_json,
                summary = EXCLUDED.summary,
                computed_at = now()
            """,
            [row_id, plan.league_id, plan.roster_id, plan.plan_type, items_json, plan.summary],
        )

    def get_action_plan(self, league_id: str, roster_id: int) -> ActionPlan | None:
        row = self._conn.execute(
            """
            SELECT CAST(computed_at AS VARCHAR), plan_type, items_json, summary
            FROM action_plans
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            return None
        return ActionPlan(
            league_id=league_id,
            roster_id=roster_id,
            generated_at=str(row[0]),
            plan_type=str(row[1]),
            items=_loads(str(row[2]), []),
            summary=str(row[3]),
        )

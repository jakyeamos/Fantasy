from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

import duckdb

from fantasy.waiver.constants import BUILD_TEMPLATE_HINTS, BUILD_TEMPLATE_MAP
from fantasy.waiver.models import StartupContext, StartupPickValuation


def detect_startup_mode(draft_status: str) -> bool:
    return draft_status in ("pre_draft", "drafting")


def assign_build_template(direction_label: str) -> Literal["win_now", "balanced", "rebuild"]:
    return BUILD_TEMPLATE_MAP.get(direction_label, "balanced")  # type: ignore[return-value]


def evaluate_pick_recommendations(
    *,
    current_score: float,
    next_tier_score: float | None,
    slots_to_next_tier_break: int | None,
    same_tier_remaining_in_draft: int,
) -> tuple[bool, bool, str | None]:
    trade_up = (
        next_tier_score is not None
        and slots_to_next_tier_break is not None
        and 1 <= slots_to_next_tier_break <= 3
        and (next_tier_score - current_score) >= 20.0
    )
    trade_down = same_tier_remaining_in_draft >= 3
    if trade_up:
        return True, False, "You are within reach of the next tier break. Package up before it closes."
    if trade_down:
        return False, True, "Equivalent options remain on the board. Slide back and add extra equity."
    return False, False, None


def _tier_label(score: float) -> str:
    if score >= 80:
        return "Elite"
    if score >= 60:
        return "Core"
    if score >= 40:
        return "Upside"
    return "Depth"


class StartupEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def _draft_status(self, league_id: str) -> str:
        row = self._conn.execute(
            """
            SELECT status
            FROM draft_slots
            WHERE league_id = ?
            ORDER BY
                CASE status
                    WHEN 'drafting' THEN 0
                    WHEN 'pre_draft' THEN 1
                    WHEN 'complete' THEN 2
                    ELSE 3
                END
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        if row is None or row[0] is None:
            return "unknown"
        value = str(row[0])
        return value if value in {"pre_draft", "drafting", "complete"} else "unknown"

    def _direction_label(self, league_id: str, roster_id: int) -> str:
        row = self._conn.execute(
            """
            SELECT primary_label
            FROM team_directions
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        return str(row[0]) if row and row[0] else "fringe_playoff"

    def _league_size(self, league_id: str) -> int:
        row = self._conn.execute(
            """
            SELECT COUNT(*)
            FROM rosters
            WHERE league_id = ?
            """,
            [league_id],
        ).fetchone()
        return max(1, int(row[0] or 0)) if row else 12

    def compute_context(self, league_id: str, roster_id: int) -> StartupContext:
        draft_status = self._draft_status(league_id)
        direction_label = self._direction_label(league_id, roster_id)
        build_template = assign_build_template(direction_label)
        league_size = self._league_size(league_id)

        season_row = self._conn.execute(
            """
            SELECT season
            FROM leagues
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        current_season = int(season_row[0]) if season_row and season_row[0] is not None else None

        query = """
            SELECT pick_owner_roster_id, pick_year, pick_round, expected_draft_slot, demand_adjusted_value
            FROM pick_values
            WHERE league_id = ?
        """
        params: list[object] = [league_id]
        if current_season is not None:
            query += " AND pick_year = ?"
            params.append(current_season)
        if roster_id > 0:
            query += " AND pick_owner_roster_id = ?"
            params.append(roster_id)
        query += " ORDER BY pick_round, expected_draft_slot, demand_adjusted_value DESC"
        rows = self._conn.execute(query, params).fetchall()

        round_counts: dict[int, int] = {}
        raw_rows: list[dict[str, object]] = []
        for _, _, pick_round, _, demand_adjusted_value in rows:
            round_no = int(pick_round)
            round_counts[round_no] = round_counts.get(round_no, 0) + 1
            raw_rows.append(
                {
                    "pick_round": round_no,
                    "pick_slot_number": len(raw_rows) + 1,
                    "pick_slot": f"{round_no}.{str(round_counts[round_no]).zfill(2)}",
                    "pick_value": float(demand_adjusted_value or 0.0),
                }
            )

        tiered_rows = [
            {
                **row,
                "tier_label": _tier_label(float(row["pick_value"])),
            }
            for row in raw_rows
        ]

        valuations: list[StartupPickValuation] = []
        for index, row in enumerate(tiered_rows):
            next_tier_score: float | None = None
            slots_to_next_tier_break: int | None = None
            for offset in range(1, 4):
                lookup_index = index - offset
                if lookup_index < 0:
                    break
                previous = tiered_rows[lookup_index]
                if previous["tier_label"] != row["tier_label"]:
                    next_tier_score = float(previous["pick_value"])
                    slots_to_next_tier_break = offset
                    break
            same_tier_remaining = sum(
                1 for later in tiered_rows[index + 1 :] if later["tier_label"] == row["tier_label"]
            )
            trade_up, trade_down, reasoning = evaluate_pick_recommendations(
                current_score=float(row["pick_value"]),
                next_tier_score=next_tier_score,
                slots_to_next_tier_break=slots_to_next_tier_break,
                same_tier_remaining_in_draft=same_tier_remaining,
            )
            valuations.append(
                StartupPickValuation(
                    pick_slot=str(row["pick_slot"]),
                    pick_slot_number=int(row["pick_slot_number"]),
                    projected_player_name=None,
                    projected_player_id=None,
                    tier_label=str(row["tier_label"]),
                    trade_up_recommended=trade_up,
                    trade_down_recommended=trade_down,
                    trade_reasoning=reasoning,
                    pick_value=float(row["pick_value"]),
                )
            )

        return StartupContext(
            league_id=league_id,
            draft_status=draft_status,  # type: ignore[arg-type]
            startup_mode_available=detect_startup_mode(draft_status),
            build_template=build_template,
            direction_label=direction_label,
            build_template_hint=BUILD_TEMPLATE_HINTS[build_template],
            pick_valuations=valuations[: max(league_size, 12)],
            computed_at=datetime.now(timezone.utc).isoformat(),
        )


__all__ = [
    "StartupEngine",
    "assign_build_template",
    "detect_startup_mode",
    "evaluate_pick_recommendations",
]

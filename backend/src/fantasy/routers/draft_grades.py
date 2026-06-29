from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Literal

import duckdb
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from fantasy.routers.deps import get_read_db_conn

router = APIRouter(prefix="/draft-grades", tags=["draft-grades"])


class DraftGradeAtTime(BaseModel):
    model_config = ConfigDict(frozen=False)

    status: Literal["available", "unavailable"]
    note: str
    value: float | None = None


class DraftGradeSelection(BaseModel):
    model_config = ConfigDict(frozen=False)

    draft_id: str
    roster_id: int
    roster_name: str
    player_id: str
    player_name: str
    position: str | None
    pick_slot: int
    round_number: int
    season: int
    draft_type: Literal["rookie", "startup"]
    current_value: float
    expected_value: float
    value_delta: float
    rank_delta: int
    grade_score: float
    grade_label: str
    rationale: str
    at_time: DraftGradeAtTime


class DraftGradeTeamSummary(BaseModel):
    model_config = ConfigDict(frozen=False)

    roster_id: int
    roster_name: str
    pick_count: int
    average_grade: float
    total_value_delta: float
    best_pick: DraftGradeSelection | None = None
    weakest_pick: DraftGradeSelection | None = None


class DraftGradesResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    selections: list[DraftGradeSelection]
    team_summaries: list[DraftGradeTeamSummary]
    best_value: DraftGradeSelection | None = None
    biggest_reach: DraftGradeSelection | None = None
    best_team: DraftGradeTeamSummary | None = None
    weakest_team: DraftGradeTeamSummary | None = None


def _grade_label(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 72:
        return "B"
    if score >= 58:
        return "C"
    if score >= 45:
        return "D"
    return "F"


class DraftGradesService:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def build(self, league_id: str) -> DraftGradesResponse:
        rows = self._conn.execute(
            """
            SELECT
                dps.draft_id,
                dps.roster_id,
                ANY_VALUE(COALESCE(r.owner_display_name, r.owner_id, CAST(dps.roster_id AS VARCHAR))) AS roster_name,
                dps.player_id,
                ANY_VALUE(COALESCE(p.full_name, pmo.player_name, dps.player_id)) AS player_name,
                ANY_VALUE(COALESCE(dps.position, p.position, pmo.position)) AS player_position,
                dps.pick_slot,
                dps.round_number,
                dps.season,
                dps.draft_type,
                dps.ingested_at,
                COALESCE(MAX(pv.lens_market), 0.0) AS current_market,
                COALESCE(MAX(pv.lens_team_fit), 0.0) AS team_fit,
                MIN(pmo.predicted_tier) AS predicted_tier,
                MIN(pmo.tier) AS model_tier
            FROM draft_pick_selections dps
            LEFT JOIN rosters r
              ON r.league_id = dps.league_id
             AND r.roster_id = dps.roster_id
            LEFT JOIN players p
              ON p.player_id = dps.player_id
            LEFT JOIN player_values pv
              ON pv.league_id = dps.league_id
             AND pv.player_id = dps.player_id
            LEFT JOIN prospect_model_outputs pmo
              ON pmo.league_id = dps.league_id
             AND pmo.player_id = dps.player_id
             AND pmo.draft_season = dps.season
            WHERE dps.league_id = ?
            GROUP BY
                dps.draft_id, dps.roster_id, dps.player_id,
                dps.pick_slot, dps.round_number,
                dps.season, dps.draft_type, dps.ingested_at
            ORDER BY dps.season DESC, dps.draft_id, dps.pick_slot
            """,
            [league_id],
        ).fetchall()
        raw = [self._row_dict(row) for row in rows]
        expected_by_key = self._expected_values(raw)
        current_rank_by_key = self._current_ranks(raw)
        selections: list[DraftGradeSelection] = []
        for item in raw:
            key = (item["draft_id"], item["draft_type"], item["season"])
            expected = expected_by_key[key].get(item["pick_slot"], 0.0)
            current_value = self._selection_current_value(item)
            rank_delta = int(item["pick_slot"]) - current_rank_by_key[key][item["player_id"]]
            value_delta = current_value - expected
            grade = max(
                0.0,
                min(
                    100.0,
                    60.0
                    + rank_delta * 4.0
                    + value_delta * 35.0
                    + float(item["team_fit"] or 0.0) * 8.0,
                ),
            )
            at_time = self._at_time_value(
                league_id,
                str(item["player_id"]),
                item["ingested_at"],
            )
            position = str(item["position"]) if item["position"] is not None else None
            label = _grade_label(grade)
            selections.append(
                DraftGradeSelection(
                    draft_id=str(item["draft_id"]),
                    roster_id=int(item["roster_id"]),
                    roster_name=str(item["roster_name"]),
                    player_id=str(item["player_id"]),
                    player_name=str(item["player_name"]),
                    position=position,
                    pick_slot=int(item["pick_slot"]),
                    round_number=int(item["round_number"]),
                    season=int(item["season"]),
                    draft_type="rookie" if str(item["draft_type"]) == "rookie" else "startup",
                    current_value=round(current_value, 4),
                    expected_value=round(expected, 4),
                    value_delta=round(value_delta, 4),
                    rank_delta=rank_delta,
                    grade_score=round(grade, 1),
                    grade_label=label,
                    rationale=self._rationale(rank_delta, value_delta, position, label),
                    at_time=at_time,
                )
            )
        summaries = self._summaries(selections)
        return DraftGradesResponse(
            league_id=league_id,
            selections=selections,
            team_summaries=summaries,
            best_value=max(selections, key=lambda item: item.value_delta, default=None),
            biggest_reach=min(selections, key=lambda item: item.value_delta, default=None),
            best_team=max(summaries, key=lambda item: item.average_grade, default=None),
            weakest_team=min(summaries, key=lambda item: item.average_grade, default=None),
        )

    def _row_dict(self, row: tuple) -> dict[str, object]:
        columns = [
            "draft_id",
            "roster_id",
            "roster_name",
            "player_id",
            "player_name",
            "position",
            "pick_slot",
            "round_number",
            "season",
            "draft_type",
            "ingested_at",
            "current_market",
            "team_fit",
            "predicted_tier",
            "model_tier",
        ]
        return dict(zip(columns, row, strict=False))

    def _selection_current_value(self, item: dict[str, object]) -> float:
        market = float(item["current_market"] or 0.0)
        if market > 0:
            return market
        tier = item["model_tier"] or item["predicted_tier"]
        if tier is None:
            return 0.25
        return max(0.05, 0.9 - (float(tier) - 1.0) * 0.12)

    def _expected_values(
        self,
        rows: list[dict[str, object]],
    ) -> dict[tuple[str, str, int], dict[int, float]]:
        grouped: dict[tuple[str, str, int], list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            grouped[(str(row["draft_id"]), str(row["draft_type"]), int(row["season"]))].append(row)
        result: dict[tuple[str, str, int], dict[int, float]] = {}
        for key, group in grouped.items():
            sorted_values = sorted(
                (self._selection_current_value(row) for row in group),
                reverse=True,
            )
            result[key] = {
                int(row["pick_slot"]): sorted_values[min(index, len(sorted_values) - 1)]
                for index, row in enumerate(sorted(group, key=lambda item: int(item["pick_slot"])))
            }
        return result

    def _current_ranks(
        self,
        rows: list[dict[str, object]],
    ) -> dict[tuple[str, str, int], dict[str, int]]:
        grouped: dict[tuple[str, str, int], list[dict[str, object]]] = defaultdict(list)
        for row in rows:
            grouped[(str(row["draft_id"]), str(row["draft_type"]), int(row["season"]))].append(row)
        ranks: dict[tuple[str, str, int], dict[str, int]] = {}
        for key, group in grouped.items():
            sorted_group = sorted(group, key=self._selection_current_value, reverse=True)
            ranks[key] = {
                str(row["player_id"]): index + 1
                for index, row in enumerate(sorted_group)
            }
        return ranks

    def _at_time_value(
        self,
        league_id: str,
        player_id: str,
        event_at: datetime | None,
    ) -> DraftGradeAtTime:
        if event_at is None:
            return DraftGradeAtTime(
                status="unavailable",
                note="Draft selection has no stored timestamp for at-time replay.",
            )
        row = self._conn.execute(
            """
            SELECT payload_json
            FROM league_snapshots
            WHERE league_id = ? AND snapshot_at <= ?
            ORDER BY snapshot_at DESC, id DESC
            LIMIT 1
            """,
            [league_id, event_at],
        ).fetchone()
        if row is None:
            return DraftGradeAtTime(
                status="unavailable",
                note="No prior league snapshot exists for this draft pick.",
            )
        import json

        payload = json.loads(row[0])
        for roster in payload.get("state", {}).get("rosters", []):
            for player in roster.get("player_values", []):
                if str(player.get("player_id")) == player_id and player.get("lens_market") is not None:
                    return DraftGradeAtTime(
                        status="available",
                        note="Nearest prior snapshot player value.",
                        value=round(float(player["lens_market"]), 4),
                    )
        return DraftGradeAtTime(
            status="unavailable",
            note="Prior snapshot exists but does not contain this player value.",
        )

    def _rationale(
        self,
        rank_delta: int,
        value_delta: float,
        position: str | None,
        label: str,
    ) -> str:
        if rank_delta > 0:
            rank_text = f"{rank_delta} slot current-value steal"
        elif rank_delta < 0:
            rank_text = f"{abs(rank_delta)} slot current-value reach"
        else:
            rank_text = "slot matched current value"
        direction = "above" if value_delta >= 0 else "below"
        return f"{label} grade: {rank_text}; {position or 'UNKNOWN'} value is {abs(value_delta):.2f} {direction} the slot baseline."

    def _summaries(self, selections: list[DraftGradeSelection]) -> list[DraftGradeTeamSummary]:
        grouped: dict[int, list[DraftGradeSelection]] = defaultdict(list)
        for selection in selections:
            grouped[selection.roster_id].append(selection)
        summaries: list[DraftGradeTeamSummary] = []
        for roster_id, picks in grouped.items():
            summaries.append(
                DraftGradeTeamSummary(
                    roster_id=roster_id,
                    roster_name=picks[0].roster_name,
                    pick_count=len(picks),
                    average_grade=round(
                        sum(pick.grade_score for pick in picks) / max(len(picks), 1),
                        1,
                    ),
                    total_value_delta=round(sum(pick.value_delta for pick in picks), 4),
                    best_pick=max(picks, key=lambda pick: pick.value_delta, default=None),
                    weakest_pick=min(picks, key=lambda pick: pick.value_delta, default=None),
                )
            )
        summaries.sort(key=lambda item: item.average_grade, reverse=True)
        return summaries


@router.get("/{league_id}", response_model=DraftGradesResponse)
def get_draft_grades(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> DraftGradesResponse:
    return DraftGradesService(conn).build(league_id)

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from statistics import mean
from typing import Any

import duckdb

from fantasy.profiling.constants import PICK_VALUE_NORMALIZED
from fantasy.rookie.models import TendencyWarning
from fantasy.rookie.rookie_engine import RookieEngine
from fantasy.rookie_pick.constants import (
    MIN_PICK_TRADE_FOR_PREMIUM,
    MIN_ROOKIE_PICK_EVIDENCE,
)
from fantasy.rookie_pick.models import DraftPickSelection, RookiePickProfile
from fantasy.rookie_pick.rookie_pick_repo import RookiePickRepo


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


class RookiePickProfileEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._repo = RookiePickRepo(conn)

    def _load_pick_trades(self, league_id: str, roster_id: int) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT transaction_id, roster_ids, draft_picks
            FROM transactions
            WHERE league_id = ? AND type = 'trade'
            ORDER BY created_at ASC NULLS LAST, transaction_id ASC
            """,
            [league_id],
        ).fetchall()
        pick_trades: list[dict[str, Any]] = []
        for row in rows:
            roster_ids = [int(value) for value in _loads(row[1], [])]
            if roster_id not in roster_ids:
                continue
            draft_picks = _loads(row[2], [])
            if not draft_picks:
                continue
            pick_trades.append(
                {
                    "transaction_id": str(row[0]),
                    "roster_ids": roster_ids,
                    "draft_picks": draft_picks,
                }
            )
        return pick_trades

    def _parse_pick_trade(
        self, trade: dict[str, Any], roster_id: int
    ) -> tuple[list[int], list[int]]:
        received: list[int] = []
        sent: list[int] = []
        for pick in trade.get("draft_picks", []):
            round_number = int(pick.get("round") or 0)
            if round_number <= 0:
                continue
            if pick.get("owner_id") is not None and int(pick.get("owner_id")) == roster_id:
                received.append(round_number)
            if (
                pick.get("previous_owner_id") is not None
                and int(pick.get("previous_owner_id")) == roster_id
            ):
                sent.append(round_number)
        return received, sent

    def _compute_pick_premium(
        self, pick_trades: list[dict[str, Any]], roster_id: int
    ) -> tuple[float | None, int]:
        receiving_deltas: list[float] = []
        for trade in pick_trades:
            received, sent = self._parse_pick_trade(trade, roster_id)
            if not received:
                continue
            received_value = sum(PICK_VALUE_NORMALIZED.get(round_no, 0.1) for round_no in received)
            sent_value = sum(PICK_VALUE_NORMALIZED.get(round_no, 0.1) for round_no in sent)
            receiving_deltas.append(received_value - sent_value)
        evidence = len(pick_trades)
        if len(receiving_deltas) < MIN_PICK_TRADE_FOR_PREMIUM:
            return None, evidence
        return round(-mean(receiving_deltas), 3), evidence

    def _compute_positional_tendency(
        self,
        manager_selections: list[dict[str, Any]],
        all_league_selections: list[dict[str, Any]],
    ) -> dict[str, float]:
        tracked_positions = ("QB", "RB", "WR", "TE")

        def _shares(rows: list[dict[str, Any]]) -> dict[str, float]:
            relevant = [
                str(row.get("position") or "").upper()
                for row in rows
                if str(row.get("position") or "").upper() in tracked_positions
            ]
            total = len(relevant)
            if total == 0:
                return {position: 0.0 for position in tracked_positions}
            counts = Counter(relevant)
            return {
                position: counts.get(position, 0) / total
                for position in tracked_positions
            }

        manager_share = _shares(manager_selections)
        league_share = _shares(all_league_selections)
        return {
            position: round(manager_share[position] - league_share[position], 3)
            for position in tracked_positions
        }

    def _compute_dominant_archetype(self, selections: list[dict[str, Any]]) -> str | None:
        counts = Counter(
            str(selection.get("archetype_label"))
            for selection in selections
            if selection.get("archetype_label")
        )
        if not counts:
            return None
        archetype, count = counts.most_common(1)[0]
        return archetype if count >= 2 else None

    def _compute_archetype_pattern(self, selections: list[dict[str, Any]]) -> dict[str, int]:
        counts = Counter(
            str(selection.get("archetype_label"))
            for selection in selections
            if selection.get("archetype_label")
        )
        return dict(counts)

    def _map_archetype_label(self, player_id: str) -> str | None:
        row = self._conn.execute(
            """
            SELECT position, metadata_blob
            FROM players
            WHERE player_id = ?
            LIMIT 1
            """,
            [player_id],
        ).fetchone()
        if row is None:
            return None
        try:
            return RookieEngine(self._conn)._assign_archetype(
                {
                    "position": str(row[0] or ""),
                    "metadata": _loads(row[1], {}),
                    "avg_fantasy_points": 0.0,
                }
            )
        except Exception:
            return None

    def enrich_selection_archetypes(self, league_id: str) -> int:
        rows = self._conn.execute(
            """
            SELECT league_id, draft_id, roster_id, player_id, pick_slot, round_number, season, draft_type, position
            FROM draft_pick_selections
            WHERE league_id = ? AND archetype_label IS NULL
            """,
            [league_id],
        ).fetchall()
        updated = 0
        for row in rows:
            archetype = self._map_archetype_label(str(row[3]))
            selection = DraftPickSelection(
                league_id=str(row[0]),
                draft_id=str(row[1]),
                roster_id=int(row[2]),
                player_id=str(row[3]),
                pick_slot=int(row[4]),
                round_number=int(row[5]),
                season=int(row[6]),
                draft_type=str(row[7]),
                position=str(row[8]) if row[8] is not None else None,
                archetype_label=archetype,
            )
            self._repo.upsert_draft_selection(selection)
            updated += 1
        return updated

    def compute_profile(self, league_id: str, roster_id: int) -> RookiePickProfile:
        pick_trades = self._load_pick_trades(league_id, roster_id)
        pick_premium_score, pick_trade_evidence = self._compute_pick_premium(
            pick_trades, roster_id
        )
        manager_selections = self._repo.get_draft_selections(league_id, roster_id)
        all_selections = self._repo.get_all_league_selections(league_id)
        draft_selection_count = len(manager_selections)
        evidence_count = pick_trade_evidence + draft_selection_count
        profile = RookiePickProfile(
            league_id=league_id,
            roster_id=roster_id,
            computed_at=datetime.now(tz=timezone.utc).isoformat(),
            pick_premium_score=pick_premium_score,
            pick_trade_evidence=pick_trade_evidence,
            draft_selection_count=draft_selection_count,
            positional_tendency=self._compute_positional_tendency(
                manager_selections,
                all_selections,
            ),
            dominant_archetype=self._compute_dominant_archetype(manager_selections),
            archetype_pattern=self._compute_archetype_pattern(manager_selections),
            show_draft_picks_tab=evidence_count >= MIN_ROOKIE_PICK_EVIDENCE,
            draft_selection_history=manager_selections if evidence_count >= MIN_ROOKIE_PICK_EVIDENCE else [],
        )
        self._repo.upsert_profile(profile)
        return profile

    def compute_tendency_warnings(self, league_id: str) -> list[TendencyWarning]:
        rows = self._conn.execute(
            """
            SELECT r.roster_id,
                   COALESCE(r.owner_display_name, r.owner_id, 'Roster ' || CAST(r.roster_id AS VARCHAR)),
                   mrpp.pick_trade_evidence,
                   mrpp.show_draft_picks_tab,
                   mrpp.positional_tendency_json
            FROM rosters r
            LEFT JOIN manager_rookie_pick_profiles mrpp
              ON mrpp.league_id = r.league_id AND mrpp.roster_id = r.roster_id
            WHERE r.league_id = ?
            ORDER BY r.roster_id
            """,
            [league_id],
        ).fetchall()
        warnings: list[TendencyWarning] = []
        for row in rows:
            if not row[3] and int(row[2] or 0) < MIN_PICK_TRADE_FOR_PREMIUM:
                continue
            tendency = _loads(row[4], {})
            if not tendency:
                continue
            position, deviation = max(
                tendency.items(),
                key=lambda item: float(item[1]),
            )
            deviation_value = float(deviation)
            if deviation_value <= 0.15:
                continue
            selection_rows = self._repo.get_draft_selections(league_id, int(row[0]))
            relevant_count = sum(
                1
                for selection in selection_rows
                if str(selection.get("position") or "").upper() == str(position).upper()
            )
            total_count = len(selection_rows)
            manager_name = str(row[1])
            warnings.append(
                TendencyWarning(
                    warning_type="manager_tendency",
                    title=f"{manager_name} targets {position} early",
                    description=(
                        f"{manager_name} has targeted {position} in {relevant_count} of "
                        f"{total_count} draft selections in this league."
                    ),
                    affected_players=[],
                )
            )
        return warnings


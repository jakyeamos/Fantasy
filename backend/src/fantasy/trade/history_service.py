from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import duckdb

from fantasy.trade.models import (
    HistoricalAsset,
    HistoricalTradeEvaluationRow,
    HistoricalTradeParticipant,
    LeagueTradeHistoryResponse,
    TradeAsset,
    TradeRequest,
)
from fantasy.trade.trade_engine import TradeEngine


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


class TradeHistoryService:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._engine = TradeEngine(conn)

    def build(self, league_id: str) -> LeagueTradeHistoryResponse:
        rows = self._conn.execute(
            """
            SELECT transaction_id, created_at, roster_ids, adds, drops, draft_picks, week
            FROM transactions
            WHERE league_id = ? AND type = 'trade' AND status = 'complete'
            ORDER BY created_at DESC NULLS LAST, transaction_id DESC
            """,
            [league_id],
        ).fetchall()
        roster_names = self._roster_names(league_id)
        player_meta = self._player_meta()
        trades = [
            self._build_trade_row(
                league_id,
                row,
                roster_names=roster_names,
                player_meta=player_meta,
            )
            for row in rows
        ]
        return LeagueTradeHistoryResponse(league_id=league_id, trades=trades)

    def _roster_names(self, league_id: str) -> dict[int, str]:
        rows = self._conn.execute(
            """
            SELECT roster_id, COALESCE(owner_display_name, owner_id, CAST(roster_id AS VARCHAR))
            FROM rosters
            WHERE league_id = ?
            """,
            [league_id],
        ).fetchall()
        return {int(row[0]): str(row[1]) for row in rows}

    def _player_meta(self) -> dict[str, dict[str, str | None]]:
        rows = self._conn.execute(
            "SELECT player_id, full_name, position FROM players"
        ).fetchall()
        return {
            str(row[0]): {
                "name": str(row[1] or row[0]),
                "position": str(row[2]) if row[2] is not None else None,
            }
            for row in rows
        }

    def _asset_label(self, asset: TradeAsset, player_meta: dict[str, dict[str, str | None]]) -> str:
        if asset.asset_type == "pick":
            return f"{asset.pick_year or 'Future'} Round {asset.pick_round or '?'}"
        if asset.player_id is None:
            return "Unknown player"
        return str(player_meta.get(asset.player_id, {}).get("name") or asset.player_id)

    def _historical_asset(
        self,
        asset: TradeAsset,
        player_meta: dict[str, dict[str, str | None]],
    ) -> HistoricalAsset:
        meta = player_meta.get(str(asset.player_id)) if asset.player_id is not None else None
        return HistoricalAsset(
            asset_type=asset.asset_type,
            label=self._asset_label(asset, player_meta),
            player_id=asset.player_id,
            player_position=str(meta.get("position")) if meta and meta.get("position") else None,
            pick_year=asset.pick_year,
            pick_round=asset.pick_round,
            pick_original_roster_id=asset.pick_owner_roster_id,
        )

    def _parse_sides(
        self,
        adds_raw: str | None,
        drops_raw: str | None,
        picks_raw: str | None,
    ) -> dict[int, dict[str, list[TradeAsset]]]:
        sides: dict[int, dict[str, list[TradeAsset]]] = {}

        def bucket(roster_id: int) -> dict[str, list[TradeAsset]]:
            return sides.setdefault(roster_id, {"sends": [], "receives": []})

        adds = _loads(adds_raw, {})
        drops = _loads(drops_raw, {})
        if isinstance(adds, dict):
            for player_id, roster_id in adds.items():
                if roster_id is None:
                    continue
                bucket(int(roster_id))["receives"].append(
                    TradeAsset(asset_type="player", player_id=str(player_id))
                )
        if isinstance(drops, dict):
            for player_id, roster_id in drops.items():
                if roster_id is None:
                    continue
                bucket(int(roster_id))["sends"].append(
                    TradeAsset(asset_type="player", player_id=str(player_id))
                )

        picks = _loads(picks_raw, [])
        if isinstance(picks, list):
            for pick in picks:
                if not isinstance(pick, dict):
                    continue
                try:
                    asset = TradeAsset(
                        asset_type="pick",
                        pick_owner_roster_id=int(pick.get("roster_id") or 0),
                        pick_year=int(pick.get("season") or 0),
                        pick_round=int(pick.get("round") or 0),
                    )
                except (TypeError, ValueError):
                    continue
                owner_id = pick.get("owner_id")
                previous_owner_id = pick.get("previous_owner_id")
                if owner_id is not None:
                    bucket(int(owner_id))["receives"].append(asset)
                if previous_owner_id is not None:
                    bucket(int(previous_owner_id))["sends"].append(asset)
        return sides

    def _snapshot_values_before(
        self,
        league_id: str,
        event_at: datetime | None,
    ) -> dict[str, float] | None:
        if event_at is None:
            return None
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
            return None
        payload = _loads(row[0], {})
        state = payload.get("state", {}) if isinstance(payload, dict) else {}
        values: dict[str, float] = {}
        for roster in state.get("rosters", []) if isinstance(state, dict) else []:
            for player in roster.get("player_values", []):
                player_id = player.get("player_id")
                value = player.get("lens_market")
                if player_id is not None and value is not None:
                    values[str(player_id)] = float(value)
        return values

    def _at_time_delta(
        self,
        sides: dict[str, list[TradeAsset]],
        snapshot_values: dict[str, float] | None,
    ) -> tuple[str, float | None, str]:
        if snapshot_values is None:
            return "unavailable", None, "No prior league snapshot is available for this date."
        sent = sum(
            snapshot_values.get(str(asset.player_id), 0.0)
            for asset in sides["sends"]
            if asset.asset_type == "player" and asset.player_id is not None
        )
        received = sum(
            snapshot_values.get(str(asset.player_id), 0.0)
            for asset in sides["receives"]
            if asset.asset_type == "player" and asset.player_id is not None
        )
        has_player_assets = any(
            asset.asset_type == "player"
            for asset in sides["sends"] + sides["receives"]
        )
        if not has_player_assets:
            return "unavailable", None, "At-time pick valuation is not stored in snapshots yet."
        return "available", round(received - sent, 4), "Nearest prior snapshot player values."

    def _build_trade_row(
        self,
        league_id: str,
        row: tuple[Any, ...],
        *,
        roster_names: dict[int, str],
        player_meta: dict[str, dict[str, str | None]],
    ) -> HistoricalTradeEvaluationRow:
        transaction_id, created_at, roster_ids_raw, adds_raw, drops_raw, picks_raw, week = row
        parsed_roster_ids = [
            int(roster_id)
            for roster_id in (_loads(roster_ids_raw, []) or [])
            if roster_id is not None
        ]
        sides_by_roster = self._parse_sides(adds_raw, drops_raw, picks_raw)
        participant_roster_ids = sorted(set(parsed_roster_ids) | set(sides_by_roster))
        snapshot_values = self._snapshot_values_before(league_id, created_at)
        participants: list[HistoricalTradeParticipant] = []
        best_roster_id: int | None = None
        best_delta: float | None = None

        for roster_id in participant_roster_ids:
            sides = sides_by_roster.setdefault(roster_id, {"sends": [], "receives": []})
            counterparty_id = next((rid for rid in participant_roster_ids if rid != roster_id), None)
            evaluation = None
            error = None
            try:
                evaluation = self._engine.evaluate(
                    TradeRequest(
                        league_id=league_id,
                        user_roster_id=roster_id,
                        counterparty_roster_id=counterparty_id,
                        user_sends=sides["sends"],
                        user_receives=sides["receives"],
                    ),
                    include_recommendation_cards=False,
                )
                delta = evaluation.trade_balance.net_adjusted_delta if evaluation.trade_balance else None
                if delta is not None and (best_delta is None or delta > best_delta):
                    best_delta = delta
                    best_roster_id = roster_id
            except Exception as exc:
                error = f"Current replay unavailable: {exc}"
            at_time_status, at_time_delta, at_time_note = self._at_time_delta(
                sides,
                snapshot_values,
            )
            participants.append(
                HistoricalTradeParticipant(
                    roster_id=roster_id,
                    roster_name=roster_names.get(roster_id, f"Roster {roster_id}"),
                    sends=[
                        self._historical_asset(asset, player_meta)
                        for asset in sides["sends"]
                    ],
                    receives=[
                        self._historical_asset(asset, player_meta)
                        for asset in sides["receives"]
                    ],
                    current_replay=evaluation,
                    current_replay_error=error,
                    at_time_status=at_time_status,
                    at_time_delta=at_time_delta,
                    at_time_note=at_time_note,
                )
            )

        names = [roster_names.get(roster_id, f"Roster {roster_id}") for roster_id in participant_roster_ids]
        at_time_available = any(participant.at_time_status == "available" for participant in participants)
        return HistoricalTradeEvaluationRow(
            transaction_id=str(transaction_id),
            date=created_at.isoformat() if created_at is not None else None,
            week=int(week) if week is not None else None,
            participant_roster_ids=participant_roster_ids,
            participants=participants,
            summary=" ↔ ".join(names) if names else str(transaction_id),
            current_winner_roster_id=best_roster_id,
            current_winner_name=roster_names.get(best_roster_id) if best_roster_id is not None else None,
            current_best_delta=best_delta,
            at_time_status="available" if at_time_available else "unavailable",
            at_time_note=(
                "At-time snapshot values are available for player assets."
                if at_time_available
                else "No usable prior snapshot values are available for this trade."
            ),
        )

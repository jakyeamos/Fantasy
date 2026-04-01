from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import duckdb

from fantasy.trade.constants import PICK_MARKET_VALUES

from fantasy.market.models import ExternalPlayerValue, LeagueMarketSignal


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _parse_timestamp(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


class MarketService:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def _market_rank_signal(self, player_id: str) -> tuple[float, int | None]:
        total_row = self._conn.execute(
            "SELECT COUNT(*) FROM market_values"
        ).fetchone()
        total_count = int(total_row[0]) if total_row and total_row[0] is not None else 0
        row = self._conn.execute(
            """
            SELECT fantasycalc_rank
            FROM market_values
            WHERE player_id = ?
            LIMIT 1
            """,
            [player_id],
        ).fetchone()
        if row is None or row[0] is None or total_count <= 0:
            return self._adp_signal(player_id), None
        rank = int(row[0])
        return _clamp01(1.0 - (rank / max(total_count, 1))), rank

    def _adp_signal(self, player_id: str) -> float:
        row = self._conn.execute(
            """
            SELECT adp
            FROM player_adp_baseline
            WHERE player_id = ?
            LIMIT 1
            """,
            [player_id],
        ).fetchone()
        if row is None or row[0] is None:
            return 0.5
        adp = float(row[0])
        return _clamp01(1.0 - (min(adp, 250.0) / 250.0))

    def _estimate_player_asset_value(self, league_id: str, player_id: str) -> float:
        row = self._conn.execute(
            """
            SELECT lens_market
            FROM player_values
            WHERE league_id = ? AND player_id = ?
            ORDER BY computed_at DESC
            LIMIT 1
            """,
            [league_id, player_id],
        ).fetchone()
        if row and row[0] is not None:
            return _clamp01(float(row[0]))
        return self._adp_signal(player_id)

    def _estimate_pick_asset_value(self, draft_pick: dict[str, Any]) -> float:
        round_number = int(draft_pick.get("round") or 4)
        return _clamp01(float(PICK_MARKET_VALUES.get(round_number, 0.05)))

    def _trade_weight(self, created_at: str | None, index: int) -> float:
        timestamp = _parse_timestamp(created_at)
        if timestamp is None:
            return max(0.25, 1.0 - (index * 0.1))
        age_days = max(
            0.0,
            (datetime.now(timezone.utc) - timestamp.replace(tzinfo=timezone.utc)).total_seconds()
            / 86400.0,
        )
        return max(0.1, 1.0 / (1.0 + age_days / 30.0))

    def get_league_market_signal(self, player_id: str, league_id: str) -> LeagueMarketSignal:
        rows = self._conn.execute(
            """
            SELECT adds, draft_picks, CAST(created_at AS VARCHAR)
            FROM transactions
            WHERE league_id = ? AND type = 'trade'
            ORDER BY created_at DESC NULLS LAST
            LIMIT 20
            """,
            [league_id],
        ).fetchall()
        weighted_total = 0.0
        total_weight = 0.0
        trade_count = 0
        for index, row in enumerate(rows):
            adds = _loads(row[0], {})
            if player_id not in adds:
                continue
            receiving_roster = adds.get(player_id)
            opposite_players = [
                pid for pid, roster in adds.items() if pid != player_id and roster != receiving_roster
            ]
            draft_picks = _loads(row[1], [])
            asset_values = [
                self._estimate_player_asset_value(league_id, str(other_player_id))
                for other_player_id in opposite_players
            ]
            asset_values.extend(
                self._estimate_pick_asset_value(draft_pick)
                for draft_pick in draft_picks
                if draft_pick.get("owner_id") != receiving_roster
            )
            if not asset_values:
                continue
            weight = self._trade_weight(row[2], index)
            weighted_total += (sum(asset_values) / len(asset_values)) * weight
            total_weight += weight
            trade_count += 1
            if trade_count >= 5:
                break

        revealed_preference = (
            _clamp01(weighted_total / total_weight)
            if total_weight > 0
            else 0.5
        )
        return LeagueMarketSignal(
            player_id=player_id,
            league_id=league_id,
            revealed_preference=revealed_preference,
            trade_count=trade_count,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

    def get_fantasycalc_rank(self, player_id: str) -> int | None:
        row = self._conn.execute(
            """
            SELECT fantasycalc_rank
            FROM market_values
            WHERE player_id = ?
            LIMIT 1
            """,
            [player_id],
        ).fetchone()
        if row is None or row[0] is None:
            return None
        return int(row[0])

    def get_lens_market_value(self, player_id: str, league_id: str) -> float:
        fantasycalc_signal, _rank = self._market_rank_signal(player_id)
        league_signal = self.get_league_market_signal(player_id, league_id)
        return _clamp01((0.60 * league_signal.revealed_preference) + (0.40 * fantasycalc_signal))

    def store_market_values(
        self,
        player_values: list[ExternalPlayerValue],
        player_name_to_id_map: dict[str, str],
    ) -> None:
        for value in player_values:
            player_id = player_name_to_id_map.get(value.player_name.lower())
            if player_id is None:
                continue
            existing = self._conn.execute(
                """
                SELECT id
                FROM market_values
                WHERE player_id = ?
                LIMIT 1
                """,
                [player_id],
            ).fetchone()
            row_id = (
                int(existing[0])
                if existing
                else int(
                    self._conn.execute(
                        "SELECT COALESCE(MAX(id), 0) + 1 FROM market_values"
                    ).fetchone()[0]
                )
            )
            self._conn.execute(
                """
                INSERT INTO market_values (
                    id, player_id, fantasycalc_value, fantasycalc_rank, fantasycalc_trend30
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (player_id) DO UPDATE SET
                    fetched_at = CURRENT_TIMESTAMP,
                    fantasycalc_value = EXCLUDED.fantasycalc_value,
                    fantasycalc_rank = EXCLUDED.fantasycalc_rank,
                    fantasycalc_trend30 = EXCLUDED.fantasycalc_trend30
                """,
                [
                    row_id,
                    player_id,
                    value.dynasty_value,
                    value.overall_rank,
                    value.trend_30day,
                ],
            )
            if value.mfl_id is not None:
                self._conn.execute(
                    "UPDATE players SET mfl_id = ? WHERE player_id = ?",
                    [value.mfl_id, player_id],
                )


__all__ = ["MarketService"]

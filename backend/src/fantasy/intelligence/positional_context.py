from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from typing import Any

import duckdb

CORE_POSITIONS = {"QB", "RB", "WR", "TE"}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _market_from_adp(adp: float | None) -> float:
    if adp is None:
        return 0.5
    return _clamp01(1.0 - min(max(adp, 1.0), 250.0) / 250.0)


@dataclass(frozen=True)
class PositionContext:
    position: str
    fixed_starters: int
    startable_slots: float
    target_depth: int
    replacement_value: float


class PositionalContext:
    def __init__(self, conn: duckdb.DuckDBPyConnection, league_id: str, roster_id: int | None = None) -> None:
        self._conn = conn
        self.league_id = league_id
        self.roster_id = roster_id
        league_row = self._conn.execute(
            """
            SELECT roster_positions, ppr, superflex, tep, settings_blob
            FROM leagues
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        if league_row is None:
            self.roster_positions: list[str] = []
            self.ppr = 0.0
            self.superflex = False
            self.tep = False
            self.league_size = 12
        else:
            self.roster_positions = [str(slot) for slot in _loads(league_row[0], [])]
            self.ppr = float(league_row[1] or 0.0)
            self.superflex = bool(league_row[2])
            self.tep = bool(league_row[3])
            settings = _loads(league_row[4], {})
            self.league_size = max(int(settings.get("num_teams", 12) or 12), 2)

        self._position_contexts = self._build_position_contexts()
        self._market_values = self._load_market_values()
        self._roster_counts = self._load_roster_counts(roster_id)

    def base_format_scarcity(self, position: str) -> float:
        normalized = position.upper()
        base = {"QB": 0.50, "RB": 0.72, "WR": 0.68, "TE": 0.58}.get(normalized, 0.4)
        multiplier = 1.0
        if self.ppr >= 1.0:
            multiplier *= {"WR": 1.15, "TE": 1.10, "RB": 1.10}.get(normalized, 1.0)
        elif self.ppr >= 0.5:
            multiplier *= {"WR": 1.07, "TE": 1.05, "RB": 1.05}.get(normalized, 1.0)
        if self.superflex:
            multiplier *= {"QB": 1.35}.get(normalized, 1.0)
        if self.tep:
            multiplier *= {"TE": 1.15}.get(normalized, 1.0)
        return _clamp01(base * multiplier / 1.35)

    def player_market_value(self, player_id: str, position: str) -> float:
        return self._market_values.get(str(player_id), self.replacement_value(position))

    def replacement_value(self, position: str) -> float:
        context = self._position_contexts.get(position.upper())
        if context is None:
            return 0.35
        return context.replacement_value

    def positional_scarcity(self, player_id: str, position: str) -> float:
        normalized = position.upper()
        base = self.base_format_scarcity(normalized)
        if normalized not in CORE_POSITIONS:
            return base
        player_value = self.player_market_value(player_id, normalized)
        replacement = self.replacement_value(normalized)
        replacement_gap = max(0.0, player_value - replacement)
        scarcity = base + min(0.18, replacement_gap * 0.45)
        scarcity += self._tier_cliff_premium(player_id, normalized, player_value)
        if normalized == "TE" and self.tep and replacement_gap >= 0.15:
            scarcity += 0.08
        return _clamp01(scarcity)

    def team_fit(self, player_id: str, position: str, role_stability: float) -> float:
        normalized = position.upper()
        scarcity = self.positional_scarcity(player_id, normalized)
        fit = (scarcity + role_stability) / 2.0
        fit += 0.10 * self.deficit_units(normalized)
        fit -= 0.10 * self.surplus_units(normalized)
        return _clamp01(fit)

    def deficit_units(self, position: str) -> float:
        context = self._position_contexts.get(position.upper())
        if context is None:
            return 0.0
        count = self._roster_counts.get(position.upper(), 0)
        return max(0.0, context.target_depth - count) / max(context.target_depth, 1)

    def surplus_units(self, position: str) -> float:
        context = self._position_contexts.get(position.upper())
        if context is None:
            return 0.0
        count = self._roster_counts.get(position.upper(), 0)
        return max(0.0, count - context.target_depth) / max(context.target_depth, 1)

    def trade_receive_value(self, asset: dict[str, Any]) -> tuple[float, list[str]]:
        position = str(asset.get("position") or "UNKNOWN").upper()
        base = self._asset_base_fit(asset)
        deficit = self.deficit_units(position)
        surplus = self.surplus_units(position)
        value = base + 0.22 * deficit - 0.14 * surplus
        notes: list[str] = []
        if deficit > 0:
            notes.append(f"fills {position} deficit")
        elif surplus > 0:
            notes.append(f"adds to {position} surplus")
        return _clamp01(value), notes

    def trade_send_cost(self, asset: dict[str, Any]) -> tuple[float, list[str]]:
        position = str(asset.get("position") or "UNKNOWN").upper()
        base = self._asset_base_fit(asset)
        deficit = self.deficit_units(position)
        surplus = self.surplus_units(position)
        cost = base + 0.18 * deficit - 0.22 * surplus
        notes: list[str] = []
        if self.is_elite_scarce_asset(asset):
            cost += 0.16
            notes.append(f"sends scarce {position} asset")
        elif surplus > 0:
            notes.append(f"spends {position} surplus")
        return _clamp01(cost), notes

    def can_send_for_position(
        self,
        send_asset: dict[str, Any],
        receive_position: str,
        *,
        clear_overpay: bool = False,
    ) -> bool:
        send_position = str(send_asset.get("position") or "UNKNOWN").upper()
        target_position = receive_position.upper()
        if target_position not in CORE_POSITIONS:
            return True
        target_deficit = self.deficit_units(target_position)
        if target_deficit <= 0 and not clear_overpay and send_position != target_position:
            return False
        if send_position == target_position:
            return target_position != "QB" or target_deficit > 0 or clear_overpay
        if send_position not in CORE_POSITIONS:
            return True
        if self.is_elite_scarce_asset(send_asset) and not clear_overpay:
            return False
        return self.surplus_units(send_position) > 0

    def is_elite_scarce_asset(self, asset: dict[str, Any]) -> bool:
        position = str(asset.get("position") or "UNKNOWN").upper()
        if position not in CORE_POSITIONS:
            return False
        player_id = str(asset.get("player_id") or "")
        market_value = float(asset.get("lens_market") or 0.0)
        if player_id:
            market_value = max(market_value, self.player_market_value(player_id, position))
        scarcity = float(asset.get("comp_positional_scarcity") or 0.0)
        if player_id:
            scarcity = max(scarcity, self.positional_scarcity(player_id, position))
        return (
            market_value >= self.replacement_value(position) + 0.20
            and scarcity >= 0.68
            and self.surplus_units(position) <= 0
        )

    def _asset_base_fit(self, asset: dict[str, Any]) -> float:
        return _clamp01(
            (
                float(asset.get("lens_team_fit") or 0.0)
                + float(asset.get("comp_positional_scarcity") or 0.0)
                + float(asset.get("lens_market") or 0.0)
            )
            / 3.0
        )

    def _build_position_contexts(self) -> dict[str, PositionContext]:
        counts = Counter(slot for slot in self.roster_positions if slot in CORE_POSITIONS)
        flex_slots = sum(1 for slot in self.roster_positions if slot == "FLEX")
        superflex_slots = sum(1 for slot in self.roster_positions if slot == "SUPER_FLEX")
        flex_weights = {"RB": 0.35, "WR": 0.45, "TE": 0.20}
        if self.tep:
            flex_weights = {"RB": 0.30, "WR": 0.40, "TE": 0.30}
        contexts: dict[str, PositionContext] = {}
        for position in ("QB", "RB", "WR", "TE"):
            fixed = counts.get(position, 0)
            startable = float(fixed)
            if position == "QB":
                startable += float(superflex_slots)
                target_depth = max(math.ceil(startable + 1.0), 1)
            else:
                startable += flex_slots * flex_weights[position]
                bench_buffer = 2.0 if position in {"RB", "WR"} else 1.0
                if position == "TE" and self.tep:
                    bench_buffer = 2.0
                target_depth = max(math.ceil(startable + bench_buffer), 1)
            contexts[position] = PositionContext(
                position=position,
                fixed_starters=fixed,
                startable_slots=startable,
                target_depth=target_depth,
                replacement_value=0.35,
            )
        return contexts

    def _load_market_values(self) -> dict[str, float]:
        rows = self._conn.execute(
            """
            WITH adp AS (
                SELECT player_id, MIN(adp) AS adp
                FROM player_adp_baseline
                GROUP BY player_id
            ),
            value_rows AS (
                SELECT player_id, MAX(lens_market) AS market
                FROM player_values
                WHERE league_id = ?
                GROUP BY player_id
            )
            SELECT p.player_id, COALESCE(p.position, 'UNKNOWN'), adp.adp, value_rows.market
            FROM players p
            LEFT JOIN adp ON adp.player_id = p.player_id
            LEFT JOIN value_rows ON value_rows.player_id = p.player_id
            WHERE COALESCE(p.position, 'UNKNOWN') IN ('QB', 'RB', 'WR', 'TE')
            """,
            [self.league_id],
        ).fetchall()
        values: dict[str, float] = {}
        by_position: dict[str, list[float]] = {position: [] for position in CORE_POSITIONS}
        for player_id, position, adp, market in rows:
            value = float(market) if market is not None else _market_from_adp(float(adp) if adp is not None else None)
            normalized_position = str(position).upper()
            values[str(player_id)] = value
            if normalized_position in by_position:
                by_position[normalized_position].append(value)

        for position, market_values in by_position.items():
            if not market_values:
                continue
            market_values.sort(reverse=True)
            context = self._position_contexts[position]
            replacement_index = min(
                max(math.ceil(context.startable_slots * self.league_size) - 1, 0),
                len(market_values) - 1,
            )
            self._position_contexts[position] = PositionContext(
                position=context.position,
                fixed_starters=context.fixed_starters,
                startable_slots=context.startable_slots,
                target_depth=context.target_depth,
                replacement_value=market_values[replacement_index],
            )
        return values

    def _load_roster_counts(self, roster_id: int | None) -> Counter[str]:
        if roster_id is None:
            return Counter()
        row = self._conn.execute(
            """
            SELECT players, reserve, taxi
            FROM rosters
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [self.league_id, roster_id],
        ).fetchone()
        if row is None:
            return Counter()
        player_ids: list[str] = []
        for raw_ids in row:
            player_ids.extend(
                str(player_id)
                for player_id in _loads(raw_ids, [])
                if player_id not in (None, "", 0, "0")
            )
        if not player_ids:
            return Counter()
        rows = self._conn.execute(
            """
            SELECT COALESCE(position, 'UNKNOWN')
            FROM players
            WHERE player_id IN (SELECT UNNEST(?))
            """,
            [player_ids],
        ).fetchall()
        return Counter(str(row[0]).upper() for row in rows if str(row[0]).upper() in CORE_POSITIONS)

    def _tier_cliff_premium(self, player_id: str, position: str, player_value: float) -> float:
        if player_value < 0.70:
            return 0.0
        peers = sorted(
            (
                value
                for pid, value in self._market_values.items()
                if pid != str(player_id)
                and self._player_position(pid) == position
            ),
            reverse=True,
        )
        tier_count = 1 + sum(1 for value in peers if value >= player_value - 0.15)
        return max(0.0, (8 - min(tier_count, 8)) / 8.0) * 0.12

    def _player_position(self, player_id: str) -> str | None:
        row = self._conn.execute(
            """
            SELECT COALESCE(position, 'UNKNOWN')
            FROM players
            WHERE player_id = ?
            LIMIT 1
            """,
            [player_id],
        ).fetchone()
        return str(row[0]).upper() if row else None

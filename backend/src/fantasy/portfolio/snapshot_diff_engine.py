from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import duckdb

from fantasy.portfolio.constants import SNAPSHOT_ROSTER_CHANGE_THRESHOLD
from fantasy.portfolio.models import DiffRow, SnapshotAnchor

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


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _format_anchor_date(value: datetime) -> str:
    return value.strftime("%b %d, %Y")


def _humanize_field(field: str) -> str:
    if field == "pick_capital":
        return "Pick Capital Sub-score"
    return field.replace("_", " ").title()


def _humanize_label(value: str) -> str:
    return value.replace("_", " ").title()


def _format_points_delta(delta: float) -> str:
    arrow = "↑" if delta > 0 else "↓"
    return f"{arrow}{abs(delta):.0f} pts"


class SnapshotDiffEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def load_anchors(self, league_id: str) -> list[SnapshotAnchor]:
        snapshot_rows = self._conn.execute(
            """
            SELECT id, snapshot_at, snapshot_type, payload_json
            FROM league_snapshots
            WHERE league_id = ?
            ORDER BY snapshot_at DESC, id DESC
            """,
            [league_id],
        ).fetchall()
        if not snapshot_rows:
            return []

        anchors_by_id: dict[int, SnapshotAnchor] = {}

        trade_rows = self._conn.execute(
            """
            SELECT transaction_id, created_at
            FROM transactions
            WHERE league_id = ?
              AND type = 'trade'
              AND status = 'complete'
              AND created_at IS NOT NULL
            """,
            [league_id],
        ).fetchall()
        for snapshot_id, snapshot_at, _snapshot_type, _payload_json in snapshot_rows:
            snapshot_dt = snapshot_at
            if snapshot_dt is None:
                continue
            for _txn_id, created_at in trade_rows:
                if created_at is None:
                    continue
                delta_seconds = abs((snapshot_dt - created_at).total_seconds())
                if delta_seconds >= 3600:
                    continue
                anchors_by_id[int(snapshot_id)] = SnapshotAnchor(
                    snapshot_id=int(snapshot_id),
                    snapshot_at=snapshot_dt,
                    anchor_type="trade",
                    label=f"Trade - {_format_anchor_date(snapshot_dt)}",
                )
                break

        full_snapshots_by_season: dict[str, list[tuple[int, datetime]]] = {}
        for snapshot_id, snapshot_at, snapshot_type, payload_json in snapshot_rows:
            payload = _loads(payload_json, {})
            if snapshot_type == "delta":
                changed_rosters = payload.get("delta", {}).get("changed_rosters", [])
                if len(changed_rosters) >= SNAPSHOT_ROSTER_CHANGE_THRESHOLD and int(snapshot_id) not in anchors_by_id:
                    anchors_by_id[int(snapshot_id)] = SnapshotAnchor(
                        snapshot_id=int(snapshot_id),
                        snapshot_at=snapshot_at,
                        anchor_type="roster_change",
                        label=f"Roster change - {_format_anchor_date(snapshot_at)}",
                    )

            if snapshot_type != "full":
                continue
            season = str(payload.get("state", {}).get("season") or "")
            if not season:
                continue
            full_snapshots_by_season.setdefault(season, []).append((int(snapshot_id), snapshot_at))

        for season_snapshots in full_snapshots_by_season.values():
            sorted_snapshots = sorted(season_snapshots, key=lambda item: item[1])
            first_id, first_at = sorted_snapshots[0]
            if first_id not in anchors_by_id:
                anchors_by_id[first_id] = SnapshotAnchor(
                    snapshot_id=first_id,
                    snapshot_at=first_at,
                    anchor_type="season_start",
                    label=f"Season start - {_format_anchor_date(first_at)}",
                )

            last_id, last_at = sorted_snapshots[-1]
            if last_id != first_id and last_id not in anchors_by_id:
                anchors_by_id[last_id] = SnapshotAnchor(
                    snapshot_id=last_id,
                    snapshot_at=last_at,
                    anchor_type="season_end",
                    label=f"Season end - {_format_anchor_date(last_at)}",
                )

        return sorted(
            anchors_by_id.values(),
            key=lambda anchor: (anchor.snapshot_at, anchor.snapshot_id),
            reverse=True,
        )

    def _departure_type(self, league_id: str, roster_id: int, player_id: str, snapshot_at: datetime) -> str:
        rows = self._conn.execute(
            """
            SELECT type, roster_ids, adds, drops, created_at
            FROM transactions
            WHERE league_id = ?
              AND created_at IS NOT NULL
              AND created_at >= ?
            ORDER BY created_at DESC
            """,
            [league_id, snapshot_at],
        ).fetchall()
        for txn_type, roster_ids_raw, adds_raw, drops_raw, _created_at in rows:
            roster_ids = {int(value) for value in _loads(roster_ids_raw, []) if value is not None}
            if roster_id not in roster_ids:
                continue
            adds = _loads(adds_raw, {})
            drops = _loads(drops_raw, {})
            if player_id not in adds and player_id not in drops:
                continue
            if str(txn_type) == "trade":
                return "Traded"
            if player_id in drops:
                return "Dropped"
        return "Removed"

    def _current_capital_score(self, league_id: str, roster_id: int) -> float | None:
        try:
            from fantasy.picks.pick_engine import PickEngine

            return PickEngine(self._conn).compute_capital_score(league_id, roster_id)
        except Exception:
            return None

    def compute_diff(self, league_id: str, snapshot_id: int, roster_id: int) -> list[DiffRow]:
        snapshot_row = self._conn.execute(
            """
            SELECT payload_json, snapshot_at
            FROM league_snapshots
            WHERE id = ? AND league_id = ?
            LIMIT 1
            """,
            [snapshot_id, league_id],
        ).fetchone()
        if snapshot_row is None:
            return []

        payload = _loads(snapshot_row[0], {})
        snapshot_at = snapshot_row[1]
        historical_roster = None
        for roster in payload.get("state", {}).get("rosters", []):
            if int(roster.get("roster_id", 0)) == roster_id:
                historical_roster = roster
                break
        if historical_roster is None:
            return []

        diffs: list[DiffRow] = []

        current_direction = self._conn.execute(
            """
            SELECT primary_label
            FROM team_directions
            WHERE league_id = ? AND roster_id = ?
            ORDER BY computed_at DESC
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        old_direction = str((historical_roster.get("direction") or {}).get("label") or "")
        new_direction = str(current_direction[0]) if current_direction and current_direction[0] is not None else ""
        if old_direction and new_direction and old_direction != new_direction:
            diffs.append(
                DiffRow(
                    field="Direction",
                    field_type="direction_label",
                    old_value=_humanize_label(old_direction),
                    new_value=_humanize_label(new_direction),
                    display_string=f"{_humanize_label(old_direction)} -> {_humanize_label(new_direction)}",
                )
            )

        scorecard_row = self._conn.execute(
            """
            SELECT win_now, future_value, depth, pick_capital, flexibility,
                   fragility, age_risk, liquidity, positional_insulation
            FROM team_scorecards
            WHERE league_id = ? AND roster_id = ?
            ORDER BY computed_at DESC
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        historical_scorecard = historical_roster.get("scorecard") or {}
        if scorecard_row is not None and historical_scorecard:
            for field_name, current_value in zip(SCORECARD_FIELDS, scorecard_row, strict=False):
                if field_name not in historical_scorecard or current_value is None:
                    continue
                delta = (float(current_value) - float(historical_scorecard[field_name])) * 100.0
                if abs(delta) < 1.0:
                    continue
                diffs.append(
                    DiffRow(
                        field=_humanize_field(field_name),
                        field_type="scorecard",
                        delta=round(delta, 2),
                        old_value=str(round(float(historical_scorecard[field_name]) * 100.0, 2)),
                        new_value=str(round(float(current_value) * 100.0, 2)),
                        display_string=_format_points_delta(delta),
                    )
                )

        current_player_rows = self._conn.execute(
            """
            SELECT pv.player_id, COALESCE(p.full_name, pv.player_id), COALESCE(p.position, 'UNKNOWN'), pv.lens_market
            FROM player_values pv
            LEFT JOIN players p ON p.player_id = pv.player_id
            WHERE pv.league_id = ? AND pv.roster_id = ?
            ORDER BY pv.player_id
            """,
            [league_id, roster_id],
        ).fetchall()
        current_players = {
            str(row[0]): {
                "player_name": str(row[1]),
                "position": str(row[2]),
                "lens_market": float(row[3]) if row[3] is not None else None,
            }
            for row in current_player_rows
        }
        historical_players = {
            str(player.get("player_id")): player
            for player in historical_roster.get("player_values", [])
            if player.get("player_id") is not None
        }

        for player_id, historical_player in historical_players.items():
            current_player = current_players.get(player_id)
            historical_value = historical_player.get("lens_market")
            if current_player is None:
                departure_type = self._departure_type(league_id, roster_id, player_id, snapshot_at)
                diffs.append(
                    DiffRow(
                        field=str(historical_player.get("player_name") or player_id),
                        field_type="departed",
                        display_string=f"{departure_type} (was {historical_player.get('position') or 'UNKNOWN'})",
                    )
                )
                continue
            if historical_value is None or current_player["lens_market"] is None:
                continue
            delta = (float(current_player["lens_market"]) - float(historical_value)) * 100.0
            if abs(delta) < 1.0:
                continue
            diffs.append(
                DiffRow(
                    field=current_player["player_name"],
                    field_type="player_value",
                    delta=round(delta, 2),
                    old_value=str(round(float(historical_value) * 100.0, 2)),
                    new_value=str(round(float(current_player["lens_market"]) * 100.0, 2)),
                    display_string=_format_points_delta(delta),
                )
            )

        for player_id, current_player in current_players.items():
            if player_id in historical_players:
                continue
            diffs.append(
                DiffRow(
                    field=current_player["player_name"],
                    field_type="added",
                    display_string=f"+ {current_player['player_name']} added",
                )
            )

        historical_capital = historical_roster.get("capital_score")
        current_capital = self._current_capital_score(league_id, roster_id)
        if historical_capital is not None and current_capital is not None:
            delta = round(float(current_capital) - float(historical_capital), 2)
            if abs(delta) >= 1.0:
                diffs.append(
                    DiffRow(
                        field="Pick Capital",
                        field_type="pick_capital",
                        delta=delta,
                        old_value=str(round(float(historical_capital), 2)),
                        new_value=str(round(float(current_capital), 2)),
                        display_string=_format_points_delta(delta),
                    )
                )

        return diffs

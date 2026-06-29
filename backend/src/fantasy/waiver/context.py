from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import duckdb


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _depth_order(metadata: Any) -> int | None:
    if not isinstance(metadata, dict):
        return None
    raw_order = metadata.get("depth_chart_order")
    if raw_order is None:
        return None
    try:
        return int(raw_order)
    except (TypeError, ValueError):
        return None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def format_direction(direction_label: str) -> str:
    return direction_label.replace("_", " ")


def parse_timestamp(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def roster_has_position_anchor(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    roster_id: int,
    position: str,
    candidate_adp: float | None,
) -> bool:
    roster_row = conn.execute(
        """
        SELECT players, reserve, taxi
        FROM rosters
        WHERE league_id = ? AND roster_id = ?
        LIMIT 1
        """,
        [league_id, roster_id],
    ).fetchone()
    if roster_row is None:
        return False
    player_ids: list[str] = []
    for raw_ids in roster_row:
        player_ids.extend(
            str(player_id)
            for player_id in _loads(raw_ids, [])
            if player_id not in (None, "", 0, "0")
        )
    if not player_ids:
        return False
    rows = conn.execute(
        """
        WITH adp AS (
            SELECT player_id, MIN(adp) AS adp
            FROM player_adp_baseline
            GROUP BY player_id
        ),
        values AS (
            SELECT player_id, MAX(lens_market) AS lens_market
            FROM player_values
            WHERE league_id = ?
            GROUP BY player_id
        )
        SELECT MIN(adp.adp), MAX(values.lens_market)
        FROM players p
        LEFT JOIN adp ON adp.player_id = p.player_id
        LEFT JOIN values ON values.player_id = p.player_id
        WHERE p.player_id IN (SELECT UNNEST(?))
          AND COALESCE(p.position, '') = ?
        """,
        [league_id, player_ids, position],
    ).fetchone()
    if rows is None or (rows[0] is None and rows[1] is None):
        return False
    best_adp = float(rows[0]) if rows[0] is not None else None
    best_market = float(rows[1]) if rows[1] is not None else None
    if best_market is not None and best_market >= 0.62:
        return True
    return (
        best_adp is not None
        and best_adp <= 80.0
        and (candidate_adp is None or candidate_adp >= best_adp + 75.0)
    )


def same_team_position_blocked(
    conn: duckdb.DuckDBPyConnection,
    player: dict[str, Any],
    candidate_adp: float | None,
) -> bool:
    team = player.get("team")
    position = str(player["position"])
    if team is None:
        return False
    rows = conn.execute(
        """
        WITH adp AS (
            SELECT player_id, MIN(adp) AS adp
            FROM player_adp_baseline
            GROUP BY player_id
        )
        SELECT p.player_id, adp.adp, p.metadata_blob
        FROM players p
        LEFT JOIN adp ON adp.player_id = p.player_id
        WHERE p.player_id != ?
          AND COALESCE(p.team, '') = ?
          AND COALESCE(p.position, '') = ?
        """,
        [player["player_id"], team, position],
    ).fetchall()
    candidate_order = _depth_order(player.get("metadata"))
    for _, blocker_adp, metadata_blob in rows:
        blocker_order = _depth_order(_loads(metadata_blob, {}))
        if blocker_order is not None and (
            candidate_order is None or blocker_order < candidate_order
        ):
            return True
        if (
            candidate_adp is not None
            and blocker_adp is not None
            and float(blocker_adp) <= candidate_adp - 75.0
        ):
            return True
    return False


def contextual_stash_bid_cap_pct(
    conn: duckdb.DuckDBPyConnection,
    *,
    league_id: str,
    roster_id: int,
    player: dict[str, Any],
    weak_positions: set[str],
    is_immediate_start: bool,
    adp: float | None,
) -> float | None:
    if is_immediate_start:
        return None
    position = str(player["position"])
    cap_pct: float | None = None
    if position not in weak_positions and roster_has_position_anchor(
        conn,
        league_id,
        roster_id,
        position,
        adp,
    ):
        cap_pct = 0.05
    if same_team_position_blocked(conn, player, adp):
        cap_pct = min(cap_pct if cap_pct is not None else 0.08, 0.05)
    return cap_pct

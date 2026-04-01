from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import duckdb

from fantasy.intelligence.constants import POSITIONAL_CLIFF_AGE
from fantasy.player_flags.flag_repo import FlagRepo
from fantasy.player_flags.models import PlayerContextFlag

_SKILL_POSITIONS = {"QB", "RB", "WR", "TE"}
_TRANSIENT_FLAGS = {
    "injury_recovery",
    "depth_chart_competition",
    "role_expansion",
    "role_compression",
    "age_cliff_proximity",
}


def _loads(raw: str | None) -> dict[str, Any]:
    if raw is None:
        return {}
    try:
        return dict(json.loads(raw))
    except json.JSONDecodeError:
        return {}


class FlagEngine:
    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        repo: FlagRepo | None = None,
    ) -> None:
        self._conn = conn
        self._repo = repo or FlagRepo(conn)

    def derive_flags_for_player(self, player_id: str) -> list[PlayerContextFlag]:
        row = self._conn.execute(
            """
            SELECT COALESCE(position, 'UNKNOWN'),
                   team,
                   age,
                   metadata_blob
            FROM players
            WHERE player_id = ?
            LIMIT 1
            """,
            [player_id],
        ).fetchone()
        if row is None:
            self._repo.clear_flags(player_id, list(_TRANSIENT_FLAGS))
            return self._repo.get_active_flags(player_id)

        position = str(row[0] or "UNKNOWN").upper()
        team = str(row[1]) if row[1] is not None else None
        age = int(row[2]) if row[2] is not None else None
        metadata = _loads(row[3])
        now = datetime.now(timezone.utc)

        injury_status = str(metadata.get("injury_status") or "")
        depth_chart_order_raw = metadata.get("depth_chart_order")
        previous_depth_chart_order_raw = metadata.get("previous_depth_chart_order")
        previous_team = metadata.get("previous_team") or metadata.get("old_team")

        try:
            depth_chart_order = int(depth_chart_order_raw) if depth_chart_order_raw is not None else None
        except (TypeError, ValueError):
            depth_chart_order = None
        try:
            previous_depth_chart_order = (
                int(previous_depth_chart_order_raw)
                if previous_depth_chart_order_raw is not None
                else None
            )
        except (TypeError, ValueError):
            previous_depth_chart_order = None

        self._repo.clear_flags(player_id, list(_TRANSIENT_FLAGS))

        derived: list[PlayerContextFlag] = []

        if injury_status in {"IR", "Out", "Doubtful"}:
            derived.append(PlayerContextFlag(player_id=player_id, flag_type="injury_recovery"))

        if position in _SKILL_POSITIONS and depth_chart_order is not None and depth_chart_order >= 2:
            derived.append(
                PlayerContextFlag(player_id=player_id, flag_type="depth_chart_competition")
            )

        if previous_depth_chart_order is not None and depth_chart_order is not None:
            if previous_depth_chart_order >= 2 and depth_chart_order == 1:
                derived.append(
                    PlayerContextFlag(
                        player_id=player_id,
                        flag_type="role_expansion",
                        metadata={"previous_depth_chart_order": previous_depth_chart_order},
                    )
                )
            elif previous_depth_chart_order == 1 and depth_chart_order >= 2:
                derived.append(
                    PlayerContextFlag(
                        player_id=player_id,
                        flag_type="role_compression",
                        metadata={"previous_depth_chart_order": previous_depth_chart_order},
                    )
                )

        cliff_age = POSITIONAL_CLIFF_AGE.get(position)
        if age is not None and cliff_age is not None and age >= cliff_age - 1:
            derived.append(
                PlayerContextFlag(
                    player_id=player_id,
                    flag_type="age_cliff_proximity",
                    metadata={"age": age, "cliff_age": cliff_age},
                )
            )

        if previous_team and team and str(previous_team) != team:
            derived.append(
                PlayerContextFlag(
                    player_id=player_id,
                    flag_type="team_change",
                    expires_at=(now + timedelta(days=30)).isoformat(),
                    metadata={"previous_team": previous_team, "current_team": team},
                )
            )

        for flag in derived:
            self._repo.upsert_flag(flag)

        return self._repo.get_active_flags(player_id)


__all__ = ["FlagEngine"]

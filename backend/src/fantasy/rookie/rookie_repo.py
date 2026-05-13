from __future__ import annotations

import json
from typing import Any

import duckdb


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


class RookieRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def get_league_settings(self, league_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            """
            SELECT season, superflex, tep, ppr, settings_blob
            FROM leagues
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        if row is None:
            return {
                "league_id": league_id,
                "season": 2026,
                "superflex": False,
                "tep": False,
                "ppr": 0.0,
                "league_size": 12,
            }
        roster_row = self._conn.execute(
            "SELECT COUNT(*) FROM rosters WHERE league_id = ?",
            [league_id],
        ).fetchone()
        league_size = int(roster_row[0] or 12) if roster_row else 12
        settings_blob = _loads(row[4], {})
        league_size = max(int(settings_blob.get("num_teams", league_size) or league_size), 2)
        return {
            "league_id": league_id,
            "season": int(row[0] or 2026),
            "superflex": bool(row[1]),
            "tep": bool(row[2]),
            "ppr": float(row[3] or 0.0),
            "league_size": league_size,
        }

    def get_available_rookies(self, league_id: str) -> list[dict[str, Any]]:
        prospect_rows = self._get_available_rookies_from_prospect_outputs(league_id)
        if prospect_rows:
            return prospect_rows

        league_settings = self.get_league_settings(league_id)
        current_season = int(league_settings["season"])
        rows = self._conn.execute(
            """
            SELECT
                p.player_id,
                p.full_name,
                p.position,
                p.team,
                p.age,
                p.metadata_blob,
                COALESCE(
                    b.adp,
                    TRY_CAST(json_extract_string(p.metadata_blob, '$.adp') AS DOUBLE),
                    999.0
                ) AS adp,
                COALESCE(stats.seasons_played, 0) AS seasons_played,
                COALESCE(stats.avg_fantasy_points, 0.0) AS avg_fantasy_points
            FROM players p
            LEFT JOIN player_adp_baseline b ON b.player_id = p.player_id
            LEFT JOIN (
                SELECT
                    player_id,
                    COUNT(DISTINCT season) AS seasons_played,
                    AVG(fantasy_points) AS avg_fantasy_points
                FROM player_stats_weekly
                GROUP BY player_id
            ) stats ON stats.player_id = p.player_id
            WHERE p.position IN ('QB', 'RB', 'WR', 'TE')
            ORDER BY adp ASC, p.full_name ASC
            """
        ).fetchall()

        rookies: list[dict[str, Any]] = []
        for row in rows:
            metadata = _loads(row[5], {})
            draft_year = metadata.get("draft_year")
            age = int(row[4]) if row[4] is not None else None
            seasons_played = int(row[7] or 0)
            is_candidate = False
            if draft_year is not None:
                try:
                    is_candidate = int(draft_year) == current_season
                except (TypeError, ValueError):
                    is_candidate = False
            if not is_candidate and age is not None and age <= 23:
                is_candidate = True
            if not is_candidate and seasons_played == 0:
                is_candidate = True
            if not is_candidate:
                continue
            rookies.append(
                {
                    "player_id": str(row[0]),
                    "full_name": str(row[1] or row[0]),
                    "position": str(row[2] or "UNKNOWN"),
                    "team": str(row[3]) if row[3] is not None else None,
                    "age": age,
                    "metadata": metadata,
                    "adp": float(row[6] or 999.0),
                    "seasons_played": seasons_played,
                    "avg_fantasy_points": float(row[8] or 0.0),
                }
            )
        return rookies

    def _get_available_rookies_from_prospect_outputs(self, league_id: str) -> list[dict[str, Any]]:
        try:
            season_row = self._conn.execute(
                """
                SELECT MAX(draft_season)
                FROM prospect_model_outputs
                WHERE league_id IN (?, '__global__')
                """,
                [league_id],
            ).fetchone()
        except duckdb.Error:
            return []

        if season_row is None or season_row[0] is None:
            return []
        draft_season = int(season_row[0])

        rows = self._conn.execute(
            """
            SELECT
                o.player_id,
                o.player_name,
                o.position,
                o.archetype_label,
                o.risk_band,
                o.tier,
                o.predicted_tier,
                o.predicted_bucket,
                o.hit_rate_bucket,
                o.overvalue_flag_direction,
                o.overvalue_magnitude,
                o.low_confidence,
                o.comps_json,
                f.age_at_draft,
                f.draft_ovr,
                f.forty,
                f.weight,
                f.height,
                f.college_rec_ypg,
                f.college_rush_ypg,
                f.college_yprr,
                f.college_ypt,
                f.college_ypc,
                f.college_ypa,
                f.college_pass_td_rate,
                f.college_qb_rush_ypg,
                f.college_scramble_rate,
                f.college_mkt_share_proxy,
                f.college_td_rate,
                f.college_completion_pct_proxy,
                f.adp
            FROM prospect_model_outputs o
            LEFT JOIN historical_prospect_features f
                ON f.player_id = o.player_id
               AND f.draft_year = o.draft_season
            WHERE o.league_id = ?
              AND o.draft_season = ?
            ORDER BY o.predicted_tier ASC, o.tier ASC, o.player_name ASC
            """,
            [league_id, draft_season],
        ).fetchall()

        if not rows:
            rows = self._conn.execute(
                """
                SELECT
                    o.player_id,
                    o.player_name,
                    o.position,
                    o.archetype_label,
                    o.risk_band,
                    o.tier,
                    o.predicted_tier,
                    o.predicted_bucket,
                    o.hit_rate_bucket,
                    o.overvalue_flag_direction,
                    o.overvalue_magnitude,
                    o.low_confidence,
                    o.comps_json,
                    f.age_at_draft,
                    f.draft_ovr,
                    f.forty,
                    f.weight,
                    f.height,
                    f.college_rec_ypg,
                    f.college_rush_ypg,
                    f.college_yprr,
                    f.college_ypt,
                    f.college_ypc,
                    f.college_ypa,
                    f.college_pass_td_rate,
                    f.college_qb_rush_ypg,
                    f.college_scramble_rate,
                    f.college_mkt_share_proxy,
                    f.college_td_rate,
                    f.college_completion_pct_proxy,
                    f.adp
                FROM prospect_model_outputs o
                LEFT JOIN historical_prospect_features f
                    ON f.player_id = o.player_id
                   AND f.draft_year = o.draft_season
                WHERE o.league_id = '__global__'
                  AND o.draft_season = ?
                ORDER BY o.predicted_tier ASC, o.tier ASC, o.player_name ASC
                """,
                [draft_season],
            ).fetchall()

        return [
            {
                "player_id": str(row[0]),
                "full_name": str(row[1]),
                "position": str(row[2]),
                "team": None,
                "age": None,
                "metadata": {
                    "draft_year": draft_season,
                    "archetype_label": str(row[3]),
                    "risk_band": str(row[4]),
                    "tier": int(row[5]),
                    "predicted_tier": int(row[6]),
                    "predicted_bucket": str(row[7]),
                    "hit_rate_bucket": str(row[8]),
                    "overvalue_flag_direction": str(row[9]) if row[9] is not None else None,
                    "overvalue_magnitude": int(row[10]) if row[10] is not None else None,
                    "low_confidence": bool(row[11]),
                    "comps": _loads(row[12], []),
                    "age_at_draft": float(row[13]) if row[13] is not None else None,
                    "draft_pick": int(row[14]) if row[14] is not None else None,
                    "draft_ovr": int(row[14]) if row[14] is not None else None,
                    "forty": float(row[15]) if row[15] is not None else None,
                    "weight": float(row[16]) if row[16] is not None else None,
                    "height": float(row[17]) if row[17] is not None else None,
                    "college_rec_ypg": float(row[18]) if row[18] is not None else None,
                    "college_rush_ypg": float(row[19]) if row[19] is not None else None,
                    "college_yprr": float(row[20]) if row[20] is not None else None,
                    "college_ypt": float(row[21]) if row[21] is not None else None,
                    "college_ypc": float(row[22]) if row[22] is not None else None,
                    "college_ypa": float(row[23]) if row[23] is not None else None,
                    "college_pass_td_rate": float(row[24]) if row[24] is not None else None,
                    "college_qb_rush_ypg": float(row[25]) if row[25] is not None else None,
                    "college_scramble_rate": float(row[26]) if row[26] is not None else None,
                    "college_mkt_share_proxy": float(row[27]) if row[27] is not None else None,
                    "college_td_rate": float(row[28]) if row[28] is not None else None,
                    "college_completion_pct_proxy": float(row[29]) if row[29] is not None else None,
                },
                "adp": float(row[30] or row[6] or row[5] or 999.0),
                "seasons_played": 0,
                "avg_fantasy_points": 0.0,
            }
            for row in rows
        ]

    def save_board_cache(self, league_id: str, class_strength_signal: float, board_json: str) -> None:
        try:
            self._conn.execute("DELETE FROM rookie_board_cache WHERE league_id = ?", [league_id])
            next_id_row = self._conn.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM rookie_board_cache"
            ).fetchone()
            next_id = int(next_id_row[0] or 1) if next_id_row else 1
            self._conn.execute(
                """
                INSERT INTO rookie_board_cache (id, league_id, computed_at, class_strength_signal, board_json)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)
                """,
                [next_id, league_id, class_strength_signal, board_json],
            )
        except duckdb.Error:
            return

    def replace_league_tendencies(self, league_id: str, tendencies: list[dict[str, Any]]) -> None:
        try:
            self._conn.execute("DELETE FROM league_draft_tendencies WHERE league_id = ?", [league_id])
            next_id_row = self._conn.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM league_draft_tendencies"
            ).fetchone()
            next_id = int(next_id_row[0] or 1) if next_id_row else 1
            for tendency in tendencies:
                self._conn.execute(
                    """
                    INSERT INTO league_draft_tendencies (
                        id,
                        league_id,
                        computed_at,
                        tendency_type,
                        position,
                        player_id,
                        player_name,
                        early_draft_slots,
                        adp_delta,
                        system_value_slot
                    ) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        next_id,
                        league_id,
                        tendency.get("tendency_type"),
                        tendency.get("position"),
                        tendency.get("player_id"),
                        tendency.get("player_name"),
                        tendency.get("early_draft_slots"),
                        tendency.get("adp_delta"),
                        tendency.get("system_value_slot"),
                    ],
                )
                next_id += 1
        except duckdb.Error:
            return

    def get_league_tendencies(self, league_id: str) -> list[dict[str, Any]]:
        try:
            rows = self._conn.execute(
                """
                SELECT tendency_type, position, player_id, player_name, early_draft_slots, adp_delta, system_value_slot
                FROM league_draft_tendencies
                WHERE league_id = ?
                ORDER BY tendency_type, COALESCE(position, ''), COALESCE(player_name, '')
                """,
                [league_id],
            ).fetchall()
        except duckdb.Error:
            return []
        return [
            {
                "tendency_type": str(row[0]),
                "position": str(row[1]) if row[1] is not None else None,
                "player_id": str(row[2]) if row[2] is not None else None,
                "player_name": str(row[3]) if row[3] is not None else None,
                "early_draft_slots": float(row[4]) if row[4] is not None else None,
                "adp_delta": float(row[5]) if row[5] is not None else None,
                "system_value_slot": int(row[6]) if row[6] is not None else None,
            }
            for row in rows
        ]

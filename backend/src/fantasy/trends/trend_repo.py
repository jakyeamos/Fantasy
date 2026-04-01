from __future__ import annotations

from typing import TYPE_CHECKING, Any

import duckdb

from fantasy.trends.constants import COMPONENT_COLS

if TYPE_CHECKING:
    from fantasy.intelligence.models import PlayerValue


def _as_float(value: Any) -> float | None:
    return float(value) if value is not None else None


class TrendRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def _next_id(self) -> int:
        return int(
            self._conn.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 FROM player_trends"
            ).fetchone()[0]
        )

    def get_player_seasons(self, player_id: str, limit: int = 2) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            f"""
            SELECT season, trend_label, confidence, delta_magnitude, adp_delta, startup_adp,
                   backfilled, {", ".join(COMPONENT_COLS)}
            FROM player_trends
            WHERE player_id = ?
            ORDER BY season DESC
            LIMIT {max(int(limit), 1)}
            """,
            [player_id],
        ).fetchall()
        columns = [
            "season",
            "trend_label",
            "confidence",
            "delta_magnitude",
            "adp_delta",
            "startup_adp",
            "backfilled",
            *COMPONENT_COLS,
        ]
        return [dict(zip(columns, row, strict=False)) for row in rows]

    def get_latest_player_row(self, player_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            f"""
            SELECT t.player_id,
                   COALESCE(p.full_name, t.player_id) AS full_name,
                   COALESCE(p.position, 'UNKNOWN') AS position,
                   COALESCE(p.age, 24) AS age,
                   t.season,
                   t.startup_adp,
                   t.backfilled,
                   {", ".join(f"t.{column}" for column in COMPONENT_COLS)}
            FROM player_trends t
            LEFT JOIN players p ON p.player_id = t.player_id
            WHERE t.player_id = ?
            ORDER BY t.season DESC
            LIMIT 1
            """,
            [player_id],
        ).fetchone()
        if row is None:
            return None
        columns = [
            "player_id",
            "full_name",
            "position",
            "age",
            "season",
            "startup_adp",
            "backfilled",
            *COMPONENT_COLS,
        ]
        return dict(zip(columns, row, strict=False))

    def get_player_baseline(self, player_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            WITH target AS (
                SELECT ? AS player_id
            ),
            stats AS (
                SELECT player_id,
                       AVG(fantasy_points) AS ppg,
                       COUNT(*) AS games_played,
                       MAX(fantasy_points) AS best_week
                FROM player_stats_weekly
                WHERE player_id = ?
                GROUP BY player_id
            )
            SELECT target.player_id,
                   COALESCE(p.full_name, b.player_name, target.player_id) AS full_name,
                   COALESCE(p.position, b.position, 'UNKNOWN') AS position,
                   COALESCE(p.age, 24) AS age,
                   b.adp AS startup_adp,
                   stats.ppg,
                   stats.games_played,
                   stats.best_week
            FROM target
            LEFT JOIN players p ON p.player_id = target.player_id
            LEFT JOIN player_adp_baseline b ON b.player_id = target.player_id
            LEFT JOIN stats ON stats.player_id = target.player_id
            """,
            [player_id, player_id],
        ).fetchone()
        if row is None:
            return None
        return {
            "player_id": str(row[0]),
            "full_name": str(row[1] or player_id),
            "position": str(row[2] or "UNKNOWN"),
            "age": int(row[3]) if row[3] is not None else 24,
            "startup_adp": _as_float(row[4]),
            "ppg": _as_float(row[5]),
            "games_played": int(row[6]) if row[6] is not None else 0,
            "best_week": _as_float(row[7]),
        }

    def list_candidate_players(self) -> list[dict[str, Any]]:
        candidates: dict[str, dict[str, Any]] = {}
        baseline_rows = self._conn.execute(
            """
            SELECT b.player_id,
                   COALESCE(p.full_name, b.player_name, b.player_id) AS full_name,
                   COALESCE(p.position, b.position, 'UNKNOWN') AS position,
                   COALESCE(p.age, 24) AS age,
                   b.adp AS startup_adp
            FROM player_adp_baseline b
            LEFT JOIN players p ON p.player_id = b.player_id
            ORDER BY b.adp ASC NULLS LAST, full_name ASC
            """
        ).fetchall()
        for row in baseline_rows:
            candidates[str(row[0])] = {
                "player_id": str(row[0]),
                "full_name": str(row[1] or row[0]),
                "position": str(row[2] or "UNKNOWN"),
                "age": int(row[3]) if row[3] is not None else 24,
                "startup_adp": _as_float(row[4]),
            }

        latest_rows = self._conn.execute(
            """
            SELECT t.player_id,
                   COALESCE(p.full_name, t.player_id) AS full_name,
                   COALESCE(p.position, 'UNKNOWN') AS position,
                   COALESCE(p.age, 24) AS age,
                   t.startup_adp,
                   t.season
            FROM player_trends t
            LEFT JOIN players p ON p.player_id = t.player_id
            ORDER BY t.player_id, t.season DESC
            """
        ).fetchall()
        seen: set[str] = set()
        for row in latest_rows:
            player_id = str(row[0])
            if player_id in seen:
                continue
            seen.add(player_id)
            candidates.setdefault(
                player_id,
                {
                    "player_id": player_id,
                    "full_name": str(row[1] or row[0]),
                    "position": str(row[2] or "UNKNOWN"),
                    "age": int(row[3]) if row[3] is not None else 24,
                    "startup_adp": _as_float(row[4]),
                },
            )

        return sorted(
            candidates.values(),
            key=lambda candidate: (
                candidate["startup_adp"] is None,
                candidate["startup_adp"] or 999.0,
                candidate["full_name"].lower(),
                candidate["player_id"],
            ),
        )

    def write_trend_row(
        self,
        *,
        player_id: str,
        season: int,
        trend_label: str | None,
        confidence: str | None,
        delta_magnitude: float,
        adp_delta: float | None,
        components: dict[str, float | None],
        startup_adp: float | None,
        backfilled: bool,
    ) -> None:
        existing = self._conn.execute(
            """
            SELECT id
            FROM player_trends
            WHERE player_id = ? AND season = ?
            LIMIT 1
            """,
            [player_id, season],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id()
        values = [components.get(column) for column in COMPONENT_COLS]
        self._conn.execute(
            f"""
            INSERT INTO player_trends (
                id, player_id, season, trend_label, confidence, delta_magnitude,
                adp_delta, {", ".join(COMPONENT_COLS)}, startup_adp, backfilled
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, {", ".join("?" for _ in COMPONENT_COLS)}, ?, ?)
            ON CONFLICT (player_id, season) DO UPDATE SET
                trend_label = EXCLUDED.trend_label,
                confidence = EXCLUDED.confidence,
                delta_magnitude = EXCLUDED.delta_magnitude,
                adp_delta = EXCLUDED.adp_delta,
                {", ".join(f"{column} = EXCLUDED.{column}" for column in COMPONENT_COLS)},
                startup_adp = EXCLUDED.startup_adp,
                backfilled = EXCLUDED.backfilled
            """,
            [
                row_id,
                player_id,
                season,
                trend_label,
                confidence,
                delta_magnitude,
                adp_delta,
                *values,
                startup_adp,
                backfilled,
            ],
        )

    def write_from_player_value(
        self,
        value: PlayerValue,
        *,
        season: int,
        startup_adp: float | None,
        backfilled: bool = False,
    ) -> None:
        components: dict[str, float | None] = {
            "comp_current_production": value.comp_current_production,
            "comp_short_term": value.comp_short_term,
            "comp_role_stability": value.comp_role_stability,
            "comp_age_curve": value.comp_age_curve,
            "comp_insulation": value.comp_insulation,
            "comp_market_liquidity": value.comp_market_liquidity,
            "comp_positional_scarcity": value.comp_positional_scarcity,
            "comp_fragility": value.comp_fragility,
            "comp_ceiling": value.comp_ceiling,
            "comp_floor": value.comp_floor,
            "comp_rerollability": value.comp_rerollability,
            "comp_contract": value.comp_contract,
        }
        self.write_trend_row(
            player_id=value.player_id,
            season=season,
            trend_label=None,
            confidence=None,
            delta_magnitude=0.0,
            adp_delta=None,
            components=components,
            startup_adp=startup_adp,
            backfilled=backfilled,
        )

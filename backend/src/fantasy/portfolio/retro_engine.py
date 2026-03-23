from __future__ import annotations

import duckdb

from fantasy.portfolio.portfolio_repo import PortfolioRepo

CONTENDER_LABELS = {"true_contender", "fragile_contender"}
BOTTOM_LABELS = {"hard_rebuild", "one_year_punt"}
MIDDLE_LABELS = {"productive_struggle", "retool", "fringe_playoff"}


def _safe_accuracy(correct: int, total: int) -> float | None:
    if total <= 0:
        return None
    return round(correct / total, 3)


class RetroEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._repo = PortfolioRepo(conn)

    def _table_exists(self, table_name: str) -> bool:
        row = self._conn.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'main'
              AND table_name = ?
            LIMIT 1
            """,
            [table_name],
        ).fetchone()
        return row is not None

    def _direction_correct(self, label: str, win_pct: float) -> bool:
        if label in CONTENDER_LABELS:
            return win_pct >= 0.55
        if label in BOTTOM_LABELS:
            return win_pct <= 0.45
        if label in MIDDLE_LABELS:
            return 0.35 <= win_pct <= 0.65
        if label == "elite_value_accumulation":
            return True
        return 0.4 <= win_pct <= 0.6

    def grade_direction_labels(self, season: str) -> dict:
        rows = self._conn.execute(
            """
            SELECT td.league_id, td.roster_id, td.primary_label, s.wins, s.losses, s.ties
            FROM team_directions td
            JOIN standings s
              ON s.league_id = td.league_id
             AND s.roster_id = td.roster_id
            JOIN leagues l
              ON l.league_id = td.league_id
            WHERE l.season = ?
            """,
            [season],
        ).fetchall()

        by_label: dict[str, dict[str, int | float | None]] = {}
        correct_total = 0
        for league_id, roster_id, label, wins, losses, ties in rows:
            total_games = int(wins or 0) + int(losses or 0) + int(ties or 0)
            win_pct = (
                (int(wins or 0) + 0.5 * int(ties or 0)) / total_games
                if total_games
                else 0.5
            )
            label_key = str(label)
            correct = self._direction_correct(label_key, win_pct)
            bucket = by_label.setdefault(label_key, {"correct": 0, "total": 0, "accuracy": None})
            bucket["total"] = int(bucket["total"]) + 1
            bucket["correct"] = int(bucket["correct"]) + int(correct)
            correct_total += int(correct)

        for bucket in by_label.values():
            bucket["accuracy"] = _safe_accuracy(int(bucket["correct"]), int(bucket["total"]))

        result = {
            "season": season,
            "status": "ok" if rows else "no_data",
            "overall_accuracy": _safe_accuracy(correct_total, len(rows)),
            "by_label": by_label,
            "sample_size": len(rows),
        }
        self._repo.save_retrospective_run("direction_labels", season, result)
        return result

    def _classify_actual_bucket(self, position: str, total_points: float) -> str:
        if position == "QB":
            if total_points >= 300:
                return "hit"
            if total_points >= 150:
                return "mediocre"
            return "bust"

        if total_points >= 200:
            return "hit"
        if total_points >= 80:
            return "mediocre"
        return "bust"

    def grade_prospect_tiers(self, season: str) -> dict:
        if not self._table_exists("prospect_model_outputs"):
            result = {
                "season": season,
                "status": "skipped",
                "reason": "prospect_model_outputs table does not exist (Phase 8 not run)",
            }
            self._repo.save_retrospective_run("prospect_tiers", season, result)
            return result

        try:
            rows = self._conn.execute(
                """
                SELECT player_id, position, predicted_tier, predicted_bucket, draft_season
                FROM prospect_model_outputs
                WHERE CAST(draft_season AS VARCHAR) = ?
                """,
                [season],
            ).fetchall()
        except duckdb.Error:
            result = {
                "season": season,
                "status": "skipped",
                "reason": "prospect_model_outputs schema is incompatible with Phase 9 expectations",
            }
            self._repo.save_retrospective_run("prospect_tiers", season, result)
            return result

        if not rows:
            result = {"season": season, "status": "no_data", "overall_accuracy": None}
            self._repo.save_retrospective_run("prospect_tiers", season, result)
            return result

        by_position: dict[str, dict[str, int | float | None]] = {}
        by_tier: dict[str, dict[str, int | float | None]] = {}
        correct_total = 0
        draft_season = int(season)

        for player_id, position, predicted_tier, predicted_bucket, _draft_season in rows:
            total_points_row = self._conn.execute(
                """
                SELECT COALESCE(SUM(fantasy_points), 0.0)
                FROM player_stats_weekly
                WHERE player_id = ?
                  AND season BETWEEN ? AND ?
                """,
                [player_id, draft_season, draft_season + 2],
            ).fetchone()
            total_points = float(total_points_row[0] or 0.0) if total_points_row else 0.0
            actual_bucket = self._classify_actual_bucket(str(position or "UNKNOWN"), total_points)
            correct = actual_bucket == str(predicted_bucket or "").strip().lower()

            position_key = str(position or "UNKNOWN")
            tier_key = str(predicted_tier)
            pos_bucket = by_position.setdefault(
                position_key, {"correct": 0, "total": 0, "accuracy": None}
            )
            pos_bucket["total"] = int(pos_bucket["total"]) + 1
            pos_bucket["correct"] = int(pos_bucket["correct"]) + int(correct)

            tier_bucket = by_tier.setdefault(tier_key, {"correct": 0, "total": 0, "accuracy": None})
            tier_bucket["total"] = int(tier_bucket["total"]) + 1
            tier_bucket["correct"] = int(tier_bucket["correct"]) + int(correct)
            correct_total += int(correct)

        for bucket in [*by_position.values(), *by_tier.values()]:
            bucket["accuracy"] = _safe_accuracy(int(bucket["correct"]), int(bucket["total"]))

        result = {
            "season": season,
            "status": "ok",
            "overall_accuracy": _safe_accuracy(correct_total, len(rows)),
            "by_position": by_position,
            "by_tier": by_tier,
            "sample_size": len(rows),
        }
        self._repo.save_retrospective_run("prospect_tiers", season, result)
        return result

from __future__ import annotations

import json
from typing import Literal

import duckdb
import polars as pl
from pydantic import BaseModel


class DataGap(BaseModel):
    name: str
    reason: str
    expected_resolution: str
    severity: Literal["warning", "info"] = "warning"

    def format(self) -> str:
        return f"{self.name}: {self.reason}. Expected resolution: {self.expected_resolution}."


class GapDetector:
    @staticmethod
    def detect_unmapped_scoring_keys(
        scoring_settings: dict[str, float], sleeper_to_nfldata_map: dict[str, str]
    ) -> list[DataGap]:
        gaps: list[DataGap] = []
        for key in scoring_settings:
            if key not in sleeper_to_nfldata_map:
                gaps.append(
                    DataGap(
                        name=f"Unmapped Scoring Key: {key}",
                        reason=(
                            f"No nfl_data_py column mapped for Sleeper scoring key '{key}'."
                        ),
                        expected_resolution=(
                            "Phase 1 - add to SLEEPER_TO_NFLDATA_MAP in nfl_data_loader.py"
                        ),
                    )
                )
        return gaps

    @staticmethod
    def detect_missing_season_stats(df: pl.DataFrame, expected_years: list[int]) -> list[DataGap]:
        if "season" not in df.columns:
            return [
                DataGap(
                    name="Season Stats Missing",
                    reason="Stats dataframe has no season column.",
                    expected_resolution="Phase 1 - verify nfl_data_py import columns.",
                )
            ]

        gaps: list[DataGap] = []
        for year in expected_years:
            if df.filter(pl.col("season") == year).height == 0:
                gaps.append(
                    DataGap(
                        name=f"{year} Season Stats",
                        reason=f"nfl_data_py has no weekly rows for season {year}.",
                        expected_resolution=(
                            "Phase 1 re-ingest after nflverse data update."
                        ),
                    )
                )
        return gaps

    @staticmethod
    def detect_incomplete_transaction_history(
        conn: duckdb.DuckDBPyConnection, league_id: str, expected_season_year: int
    ) -> list[DataGap]:
        row = conn.execute(
            """
            SELECT cursor_json
            FROM ingest_runs
            WHERE league_id = ? AND status = 'complete'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            [league_id],
        ).fetchone()

        if row is None or row[0] is None:
            return [
                DataGap(
                    name="Transaction Cursor Missing",
                    reason="No completed ingest cursor found for transaction history.",
                    expected_resolution=(
                        f"Run full ingest for season {expected_season_year}."
                    ),
                    severity="info",
                )
            ]

        try:
            cursor = json.loads(row[0])
        except json.JSONDecodeError:
            return [
                DataGap(
                    name="Transaction Cursor Invalid",
                    reason="Ingest cursor_json is not valid JSON.",
                    expected_resolution="Run a fresh full ingest to rewrite cursor_json.",
                )
            ]

        max_week = int(cursor.get("max_week_fetched", 0) or 0)
        if max_week < 18:
            return [
                DataGap(
                    name="Incomplete Transaction History",
                    reason=(
                        f"Only weeks 1-{max_week} fetched; expected through week 18 for coverage."
                    ),
                    expected_resolution="Run ingest again to fetch remaining weeks.",
                )
            ]

        return []

    @classmethod
    def collect_all(
        cls,
        conn: duckdb.DuckDBPyConnection,
        league_id: str,
        scoring_settings: dict[str, float],
        sleeper_to_nfldata_map: dict[str, str],
        stats_df: pl.DataFrame,
        expected_years: list[int],
    ) -> list[DataGap]:
        gaps: list[DataGap] = []
        gaps.extend(cls.detect_unmapped_scoring_keys(scoring_settings, sleeper_to_nfldata_map))
        gaps.extend(cls.detect_missing_season_stats(stats_df, expected_years))
        expected_year = max(expected_years) if expected_years else 0
        gaps.extend(cls.detect_incomplete_transaction_history(conn, league_id, expected_year))
        return gaps


__all__ = ["DataGap", "GapDetector"]

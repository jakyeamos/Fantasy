from __future__ import annotations

import json
from typing import Any

import duckdb
import polars as pl

from fantasy.prospects.constants import DEFAULT_LEAGUE_ID
from fantasy.prospects.models import HistoricalComp, ProspectFeatures, ProspectModelOutput, SubFlag

FEATURE_KEY_COLUMNS = ["player_id", "draft_year"]
FEATURE_MUTABLE_COLUMNS = [
    "position",
    "player_name",
    "age_at_draft",
    "draft_ovr",
    "forty",
    "weight",
    "height",
    "vertical",
    "bench",
    "cone",
    "shuttle",
    "college_games",
    "college_targets",
    "college_receptions",
    "college_receiving_yards",
    "college_receiving_tds",
    "college_routes_run",
    "college_carries",
    "college_rushing_yards",
    "college_rushing_tds",
    "college_pass_attempts",
    "college_completions",
    "college_passing_yards",
    "college_passing_tds",
    "college_interceptions",
    "college_rec_ypg",
    "college_rush_ypg",
    "college_yprr",
    "college_ypt",
    "college_ypc",
    "college_ypa",
    "college_pass_td_rate",
    "college_qb_rush_yards",
    "college_qb_rush_tds",
    "college_qb_rush_ypg",
    "college_scramble_rate",
    "college_mkt_share_proxy",
    "college_td_rate",
    "college_completion_pct_proxy",
    "adp",
    "archetype_label",
    "outcome_bucket",
]
FEATURE_COLUMNS = FEATURE_KEY_COLUMNS + FEATURE_MUTABLE_COLUMNS


def _loads(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


class ProspectRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def get_league_ids(self) -> list[str]:
        rows = self._conn.execute(
            """
            SELECT league_id
            FROM leagues
            ORDER BY league_id
            """
        ).fetchall()
        return [str(row[0]) for row in rows]

    def upsert_features(self, features: list[ProspectFeatures]) -> None:
        if not features:
            return
        df = pl.DataFrame([feature.model_dump(mode="python") for feature in features]).select(FEATURE_COLUMNS)
        update_assignments = ",\n                    ".join(
            f"{column} = EXCLUDED.{column}" for column in FEATURE_MUTABLE_COLUMNS
        )
        try:
            self._conn.register("prospect_features_df", df)
            self._conn.execute(
                f"""
                INSERT INTO historical_prospect_features
                SELECT * FROM prospect_features_df
                ON CONFLICT (player_id, draft_year) DO UPDATE SET
                    {update_assignments}
                """
            )
            self._conn.unregister("prospect_features_df")
        except Exception:
            rows = [list(row.values()) for row in df.to_dicts()]
            self._conn.executemany(
                f"""
                INSERT INTO historical_prospect_features (
                    {", ".join(FEATURE_COLUMNS)}
                )
                VALUES ({", ".join(["?"] * len(FEATURE_COLUMNS))})
                ON CONFLICT (player_id, draft_year) DO UPDATE SET
                    {update_assignments}
                """,
                rows,
            )

    def get_features_by_position(
        self,
        position: str,
        max_draft_year: int | None = None,
    ) -> list[ProspectFeatures]:
        sql = f"""
            SELECT
                {", ".join(FEATURE_COLUMNS)}
            FROM historical_prospect_features
            WHERE position = ?
        """
        params: list[Any] = [position]
        if max_draft_year is not None:
            sql += " AND draft_year <= ?"
            params.append(max_draft_year)
        sql += " ORDER BY draft_year, COALESCE(draft_ovr, 9999), player_name"
        rows = self._conn.execute(sql, params).fetchall()
        return [
            ProspectFeatures.model_validate(dict(zip(FEATURE_COLUMNS, row, strict=False)))
            for row in rows
        ]

    def upsert_model_outputs(self, outputs: list[ProspectModelOutput]) -> None:
        if not outputs:
            return
        rows = []
        for output in outputs:
            rows.append(
                {
                    "league_id": output.league_id,
                    "draft_season": output.draft_season,
                    "player_id": output.player_id,
                    "player_name": output.player_name,
                    "position": output.position,
                    "archetype_label": output.archetype_label,
                    "hit_rate_bucket": output.hit_rate_bucket,
                    "tier": output.tier,
                    "predicted_tier": output.predicted_tier,
                    "predicted_bucket": output.predicted_bucket,
                    "risk_band": output.risk_band,
                    "overvalue_flag_direction": output.overvalue_flag_direction,
                    "overvalue_magnitude": output.overvalue_magnitude,
                    "low_confidence": output.low_confidence,
                    "comps_json": json.dumps(
                        [comp.model_dump(mode="json") for comp in output.comps],
                        separators=(",", ":"),
                    ),
                    "computed_at": output.computed_at,
                }
            )
        df = pl.DataFrame(rows)
        try:
            self._conn.register("prospect_outputs_df", df)
            self._conn.execute(
                """
                INSERT INTO prospect_model_outputs
                SELECT * FROM prospect_outputs_df
                ON CONFLICT (league_id, draft_season, player_id) DO UPDATE SET
                    player_name = EXCLUDED.player_name,
                    position = EXCLUDED.position,
                    archetype_label = EXCLUDED.archetype_label,
                    hit_rate_bucket = EXCLUDED.hit_rate_bucket,
                    tier = EXCLUDED.tier,
                    predicted_tier = EXCLUDED.predicted_tier,
                    predicted_bucket = EXCLUDED.predicted_bucket,
                    risk_band = EXCLUDED.risk_band,
                    overvalue_flag_direction = EXCLUDED.overvalue_flag_direction,
                    overvalue_magnitude = EXCLUDED.overvalue_magnitude,
                    low_confidence = EXCLUDED.low_confidence,
                    comps_json = EXCLUDED.comps_json,
                    computed_at = EXCLUDED.computed_at
                """
            )
            self._conn.unregister("prospect_outputs_df")
        except Exception:
            self._conn.executemany(
                """
                INSERT INTO prospect_model_outputs (
                    league_id, draft_season, player_id, player_name, position,
                    archetype_label, hit_rate_bucket, tier, predicted_tier, predicted_bucket,
                    risk_band, overvalue_flag_direction, overvalue_magnitude, low_confidence,
                    comps_json, computed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (league_id, draft_season, player_id) DO UPDATE SET
                    player_name = EXCLUDED.player_name,
                    position = EXCLUDED.position,
                    archetype_label = EXCLUDED.archetype_label,
                    hit_rate_bucket = EXCLUDED.hit_rate_bucket,
                    tier = EXCLUDED.tier,
                    predicted_tier = EXCLUDED.predicted_tier,
                    predicted_bucket = EXCLUDED.predicted_bucket,
                    risk_band = EXCLUDED.risk_band,
                    overvalue_flag_direction = EXCLUDED.overvalue_flag_direction,
                    overvalue_magnitude = EXCLUDED.overvalue_magnitude,
                    low_confidence = EXCLUDED.low_confidence,
                    comps_json = EXCLUDED.comps_json,
                    computed_at = EXCLUDED.computed_at
                """,
                [list(row.values()) for row in rows],
            )

    def get_model_outputs(self, league_id: str) -> list[ProspectModelOutput]:
        rows = self._conn.execute(
            """
            SELECT
                league_id,
                draft_season,
                player_id,
                player_name,
                position,
                archetype_label,
                hit_rate_bucket,
                tier,
                predicted_tier,
                predicted_bucket,
                risk_band,
                overvalue_flag_direction,
                overvalue_magnitude,
                low_confidence,
                comps_json,
                computed_at
            FROM prospect_model_outputs
            WHERE league_id = ?
            ORDER BY tier, COALESCE(overvalue_magnitude, 0) DESC, player_name
            """,
            [league_id],
        ).fetchall()
        if not rows and league_id != DEFAULT_LEAGUE_ID:
            return self.get_model_outputs(DEFAULT_LEAGUE_ID)

        outputs: list[ProspectModelOutput] = []
        for row in rows:
            player_id = str(row[2])
            outputs.append(
                ProspectModelOutput(
                    league_id=str(row[0]),
                    draft_season=int(row[1]),
                    player_id=player_id,
                    player_name=str(row[3]),
                    position=str(row[4]),
                    archetype_label=str(row[5]),
                    hit_rate_bucket=str(row[6]),
                    tier=int(row[7]),
                    predicted_tier=int(row[8]),
                    predicted_bucket=str(row[9]),
                    risk_band=str(row[10]),
                    overvalue_flag_direction=str(row[11]) if row[11] is not None else None,
                    overvalue_magnitude=int(row[12]) if row[12] is not None else None,
                    low_confidence=bool(row[13]),
                    comps=[
                        HistoricalComp.model_validate(item)
                        for item in _loads(row[14], [])
                    ],
                    sub_flags=self.get_sub_flags(player_id, league_id),
                    computed_at=row[15],
                )
            )
        return outputs

    def upsert_sub_flags(self, league_id: str, player_id: str, flags: list[SubFlag]) -> None:
        self._conn.execute(
            """
            DELETE FROM prospect_sub_flags
            WHERE league_id = ? AND player_id = ?
            """,
            [league_id, player_id],
        )
        if not flags:
            return
        next_id_row = self._conn.execute(
            "SELECT COALESCE(MAX(id), 0) FROM prospect_sub_flags"
        ).fetchone()
        next_id = int(next_id_row[0] or 0) + 1 if next_id_row else 1
        payload = [
            [
                next_id + index,
                league_id,
                player_id,
                flag.signal_name,
                flag.direction,
                flag.magnitude_str,
            ]
            for index, flag in enumerate(flags)
        ]
        self._conn.executemany(
            """
            INSERT INTO prospect_sub_flags (
                id,
                league_id,
                player_id,
                signal_name,
                direction,
                magnitude_str
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            payload,
        )

    def get_sub_flags(self, player_id: str, league_id: str) -> list[SubFlag]:
        rows = self._conn.execute(
            """
            SELECT signal_name, direction, magnitude_str
            FROM prospect_sub_flags
            WHERE league_id = ? AND player_id = ?
            ORDER BY id
            """,
            [league_id, player_id],
        ).fetchall()
        if not rows and league_id != DEFAULT_LEAGUE_ID:
            return self.get_sub_flags(player_id, DEFAULT_LEAGUE_ID)
        return [
            SubFlag(
                signal_name=str(row[0]),
                direction=str(row[1]),
                magnitude_str=str(row[2]),
            )
            for row in rows
        ]

    def get_comps(self, player_id: str) -> list[HistoricalComp]:
        row = self._conn.execute(
            """
            SELECT comps_json
            FROM prospect_model_outputs
            WHERE player_id = ?
            ORDER BY computed_at DESC
            LIMIT 1
            """,
            [player_id],
        ).fetchone()
        if row is None:
            return []
        return [HistoricalComp.model_validate(item) for item in _loads(row[0], [])]

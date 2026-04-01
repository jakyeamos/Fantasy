from __future__ import annotations

from datetime import datetime, timezone
from textwrap import dedent

import duckdb
import polars as pl

from fantasy.prospects.models import HistoricalComp, ProspectFeatures, ProspectModelOutput, SubFlag
from fantasy.prospects.pipeline import run_pipeline


def _prepare_db(path: str) -> None:
    conn = duckdb.connect(path)
    conn.execute("CREATE TABLE leagues (league_id VARCHAR PRIMARY KEY)")
    conn.execute("INSERT INTO leagues VALUES ('league_a')")
    conn.execute("CREATE TABLE player_stats_weekly (player_id VARCHAR, season INTEGER, week INTEGER, fantasy_points DOUBLE, position VARCHAR)")
    conn.execute("CREATE TABLE player_adp_baseline (player_id VARCHAR, adp DOUBLE)")
    conn.execute(
        """
        CREATE TABLE historical_prospect_features (
            player_id VARCHAR,
            draft_year INTEGER,
            position VARCHAR,
            player_name VARCHAR,
            age_at_draft DOUBLE,
            draft_ovr INTEGER,
            forty DOUBLE,
            weight DOUBLE,
            height DOUBLE,
            vertical DOUBLE,
            bench INTEGER,
            cone DOUBLE,
            shuttle DOUBLE,
            college_games INTEGER,
            college_targets DOUBLE,
            college_receptions DOUBLE,
            college_receiving_yards DOUBLE,
            college_receiving_tds DOUBLE,
            college_routes_run DOUBLE,
            college_carries DOUBLE,
            college_rushing_yards DOUBLE,
            college_rushing_tds DOUBLE,
            college_pass_attempts DOUBLE,
            college_completions DOUBLE,
            college_passing_yards DOUBLE,
            college_passing_tds DOUBLE,
            college_interceptions DOUBLE,
            college_rec_ypg DOUBLE,
            college_rush_ypg DOUBLE,
            college_yprr DOUBLE,
            college_ypt DOUBLE,
            college_ypc DOUBLE,
            college_ypa DOUBLE,
            college_pass_td_rate DOUBLE,
            college_qb_rush_yards DOUBLE,
            college_qb_rush_tds DOUBLE,
            college_qb_rush_ypg DOUBLE,
            college_scramble_rate DOUBLE,
            college_mkt_share_proxy DOUBLE,
            college_td_rate DOUBLE,
            college_completion_pct_proxy DOUBLE,
            adp DOUBLE,
            archetype_label VARCHAR,
            outcome_bucket VARCHAR,
            PRIMARY KEY (player_id, draft_year)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE prospect_model_outputs (
            league_id VARCHAR,
            draft_season INTEGER,
            player_id VARCHAR,
            player_name VARCHAR,
            position VARCHAR,
            archetype_label VARCHAR,
            hit_rate_bucket VARCHAR,
            tier INTEGER,
            predicted_tier INTEGER,
            predicted_bucket VARCHAR,
            risk_band VARCHAR,
            overvalue_flag_direction VARCHAR,
            overvalue_magnitude INTEGER,
            low_confidence BOOLEAN,
            comps_json VARCHAR,
            computed_at TIMESTAMP,
            PRIMARY KEY (league_id, draft_season, player_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE prospect_sub_flags (
            id INTEGER PRIMARY KEY,
            league_id VARCHAR,
            player_id VARCHAR,
            signal_name VARCHAR,
            direction VARCHAR,
            magnitude_str VARCHAR
        )
        """
    )
    conn.close()


class _FakeLoader:
    def load_combine(self, start_year: int, end_year: int) -> pl.DataFrame:
        return pl.DataFrame()

    def load_players(self) -> pl.DataFrame:
        return pl.DataFrame()

    def load_draft_picks(self, start_year: int, end_year: int) -> pl.DataFrame:
        return pl.DataFrame()


class _FakeBuilder:
    def __init__(self, **_: object):
        pass

    def build_finish_rank_lookup(self) -> dict[str, list[int]]:
        return {"hist_hit": [1, 2, 4], "hist_med": [6, 20, 18], "hist_bust": [20, 22, 18]}

    def build_all_features(self, current_class_year: int, positions: list[str] | None = None) -> list[ProspectFeatures]:
        return [
            ProspectFeatures(player_id="hist_hit", player_name="Hit", position="QB", draft_year=2020, draft_ovr=5, age_at_draft=21, forty=4.55, weight=220, height=75, vertical=35, college_completion_pct_proxy=0.68, college_ypa=9.2, college_pass_td_rate=0.082, college_qb_rush_ypg=48.0, college_scramble_rate=0.11),
            ProspectFeatures(player_id="hist_med", player_name="Med", position="QB", draft_year=2021, draft_ovr=20, age_at_draft=22, forty=4.7, weight=218, height=74, vertical=33, college_completion_pct_proxy=0.63, college_ypa=8.0, college_pass_td_rate=0.061, college_qb_rush_ypg=24.0, college_scramble_rate=0.06),
            ProspectFeatures(player_id="hist_bust", player_name="Bust", position="QB", draft_year=2022, draft_ovr=80, age_at_draft=24, forty=4.9, weight=210, height=73, vertical=29, college_completion_pct_proxy=0.56, college_ypa=6.7, college_pass_td_rate=0.039, college_qb_rush_ypg=11.0, college_scramble_rate=0.02),
            ProspectFeatures(player_id="cur_qb", player_name="Current", position="QB", draft_year=current_class_year, draft_ovr=12, age_at_draft=21, forty=4.58, weight=221, height=75, vertical=36, college_completion_pct_proxy=0.66, college_ypa=8.8, college_pass_td_rate=0.074, college_qb_rush_ypg=42.0, college_scramble_rate=0.09, adp=2.0),
        ]


class _FakeModel:
    feature_names = [
        "age_at_draft",
        "draft_ovr",
        "forty",
        "weight",
        "height",
        "vertical",
        "college_completion_pct_proxy",
        "college_ypa",
        "college_pass_td_rate",
        "college_qb_rush_ypg",
        "college_scramble_rate",
    ]

    def __init__(self, position: str):
        self.position = position

    def walk_forward_validate(self, features_df: pl.DataFrame) -> dict:
        return {"overall_accuracy": 0.5, "per_year": [], "sample_size": features_df.height}

    def train(self, X, y) -> None:
        return None

    def train_frame(self, df: pl.DataFrame) -> None:
        return None

    def predict(self, X):
        return [{"hit": 0.55, "mediocre": 0.3, "bust": 0.15} for _ in range(len(X))]

    def predict_frame(self, df: pl.DataFrame):
        return [{"hit": 0.55, "mediocre": 0.3, "bust": 0.15} for _ in range(df.height)]


class _FakeClusterer:
    def __init__(self, position: str):
        self.position = position

    def fit(self, rows) -> None:
        return None

    def predict(self, rows):
        return ["Dual Threat" for _ in rows]

    def get_archetype_hit_rates(self, rows):
        return {"Dual Threat": {"hit": 0.5, "mediocre": 0.3, "bust": 0.2}}


class _FakeCompFinder:
    def find_comps(self, prospect, historical_pool):
        return (
            [
                HistoricalComp(player_id="hist_hit", player_name="Hit", role="ceiling", outcome_bucket="hit", match_reason="similar draft capital profile"),
                HistoricalComp(player_id="hist_med", player_name="Med", role="median", outcome_bucket="mediocre", match_reason="similar age profile"),
                HistoricalComp(player_id="hist_bust", player_name="Bust", role="floor", outcome_bucket="bust", match_reason="similar athleticism profile"),
            ],
            False,
        )


class _FakeDivergence:
    def compute_sub_flags(self, prospect, comp_features):
        return [SubFlag(signal_name="Draft Capital", direction="positive", magnitude_str="closer to round one")]

    def compute_divergence(self, player_id, model_rankings, adp_rankings, low_confidence):
        return ("undervalued", 2)


def test_run_pipeline_persists_outputs(monkeypatch, tmp_path):
    db_path = tmp_path / "phase8.duckdb"
    _prepare_db(str(db_path))

    monkeypatch.setattr("fantasy.prospects.pipeline.NflReadPyLoader", _FakeLoader)
    monkeypatch.setattr("fantasy.prospects.pipeline.FeatureBuilder", _FakeBuilder)
    monkeypatch.setattr("fantasy.prospects.pipeline.ProspectModel", _FakeModel)
    monkeypatch.setattr("fantasy.prospects.pipeline.ArchetypeClusterer", _FakeClusterer)
    monkeypatch.setattr("fantasy.prospects.pipeline.CompFinder", _FakeCompFinder)
    monkeypatch.setattr("fantasy.prospects.pipeline.DivergenceEngine", _FakeDivergence)

    result = run_pipeline(str(db_path), positions=["QB"], current_class_year=2026)

    conn = duckdb.connect(str(db_path))
    output_count = conn.execute("SELECT COUNT(*) FROM prospect_model_outputs").fetchone()[0]
    flag_count = conn.execute("SELECT COUNT(*) FROM prospect_sub_flags").fetchone()[0]
    conn.close()

    assert result["prospects_scored"] == 1
    assert output_count >= 1
    assert flag_count >= 1


def test_run_pipeline_pre_draft_mode_scores_csv_class(monkeypatch, tmp_path):
    db_path = tmp_path / "phase8.duckdb"
    csv_path = tmp_path / "2026-pre-draft.csv"
    _prepare_db(str(db_path))
    conn = duckdb.connect(str(db_path))
    conn.executemany(
        """
        INSERT INTO historical_prospect_features (
            player_id, draft_year, position, player_name, age_at_draft, draft_ovr,
            forty, weight, height, vertical, bench, cone, shuttle,
            college_games, college_targets, college_receptions, college_receiving_yards,
            college_receiving_tds, college_routes_run, college_carries, college_rushing_yards,
            college_rushing_tds, college_pass_attempts, college_completions,
            college_passing_yards, college_passing_tds, college_interceptions,
            college_rec_ypg, college_rush_ypg, college_yprr, college_ypt, college_ypc,
            college_ypa, college_pass_td_rate, college_qb_rush_yards, college_qb_rush_tds,
            college_qb_rush_ypg, college_scramble_rate, college_mkt_share_proxy,
            college_td_rate, college_completion_pct_proxy, adp, archetype_label, outcome_bucket
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("hist_hit", 2020, "QB", "Hit", 21.0, 5, 4.55, 220.0, 75.0, 35.0, None, None, None, 13, None, None, None, None, None, 110.0, 610.0, 9.0, 420.0, 280.0, 3300.0, 27.0, 7.0, None, None, None, None, None, 7.86, 0.064, 610.0, 9.0, 46.9, 0.11, None, None, 0.68, 5.0, "Dual Threat", "hit"),
            ("hist_med", 2021, "QB", "Med", 22.0, 20, 4.70, 218.0, 74.0, 33.0, None, None, None, 13, None, None, None, None, None, 70.0, 260.0, 4.0, 390.0, 240.0, 2880.0, 19.0, 10.0, None, None, None, None, None, 7.38, 0.049, 260.0, 4.0, 20.0, 0.06, None, None, 0.63, 20.0, "Dual Threat", "mediocre"),
            ("hist_bust", 2022, "QB", "Bust", 24.0, 80, 4.90, 210.0, 73.0, 29.0, None, None, None, 12, None, None, None, None, None, 38.0, 132.0, 2.0, 360.0, 204.0, 2250.0, 13.0, 11.0, None, None, None, None, None, 6.25, 0.036, 132.0, 2.0, 11.0, 0.02, None, None, 0.56, 80.0, "Dual Threat", "bust"),
        ],
    )
    conn.close()
    csv_path.write_text(
        dedent(
            """\
            player_name,position,expected_draft_ovr,age_at_draft,forty,weight,height,vertical,college_games,college_pass_attempts,college_completions,college_passing_yards,college_passing_tds,college_qb_rush_yards,college_qb_rush_tds,college_scramble_rate,adp
            Future QB,QB,4,21,4.55,220,75,35,13,430,289,3340,28,455,8,0.12,2
            """
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("fantasy.prospects.pipeline.NflReadPyLoader", _FakeLoader)
    monkeypatch.setattr("fantasy.prospects.pipeline.ProspectModel", _FakeModel)
    monkeypatch.setattr("fantasy.prospects.pipeline.ArchetypeClusterer", _FakeClusterer)
    monkeypatch.setattr("fantasy.prospects.pipeline.CompFinder", _FakeCompFinder)
    monkeypatch.setattr("fantasy.prospects.pipeline.DivergenceEngine", _FakeDivergence)

    result = run_pipeline(
        str(db_path),
        positions=["QB"],
        current_class_year=2026,
        mode="pre_draft",
        pre_draft_csv=str(csv_path),
    )

    conn = duckdb.connect(str(db_path))
    rows = conn.execute(
        """
        SELECT player_name, draft_season
        FROM prospect_model_outputs
        WHERE player_name = 'Future QB'
        """
    ).fetchall()
    conn.close()

    assert result["mode"] == "pre_draft"
    assert result["scoring_class_year"] == 2026
    assert result["prospects_scored"] == 1
    assert rows == [("Future QB", 2026), ("Future QB", 2026)]


def test_run_pipeline_pre_draft_sidecar_enrichment_merges_raw_columns(monkeypatch, tmp_path):
    db_path = tmp_path / "phase8.duckdb"
    csv_path = tmp_path / "2026-pre-draft.csv"
    enrichment_path = tmp_path / "2026-pre-draft.enrichment.csv"
    _prepare_db(str(db_path))
    conn = duckdb.connect(str(db_path))
    conn.executemany(
        """
        INSERT INTO historical_prospect_features (
            player_id, draft_year, position, player_name, age_at_draft, draft_ovr,
            forty, weight, height, vertical, bench, cone, shuttle,
            college_games, college_targets, college_receptions, college_receiving_yards,
            college_receiving_tds, college_routes_run, college_carries, college_rushing_yards,
            college_rushing_tds, college_pass_attempts, college_completions,
            college_passing_yards, college_passing_tds, college_interceptions,
            college_rec_ypg, college_rush_ypg, college_yprr, college_ypt, college_ypc,
            college_ypa, college_pass_td_rate, college_qb_rush_yards, college_qb_rush_tds,
            college_qb_rush_ypg, college_scramble_rate, college_mkt_share_proxy,
            college_td_rate, college_completion_pct_proxy, adp, archetype_label, outcome_bucket
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("hist_hit", 2020, "QB", "Hit", 21.0, 5, 4.55, 220.0, 75.0, 35.0, None, None, None, 13, None, None, None, None, None, 110.0, 610.0, 9.0, 420.0, 280.0, 3300.0, 27.0, 7.0, None, None, None, None, None, 7.86, 0.064, 610.0, 9.0, 46.9, 0.11, None, None, 0.68, 5.0, "Dual Threat", "hit"),
            ("hist_med", 2021, "QB", "Med", 22.0, 20, 4.70, 218.0, 74.0, 33.0, None, None, None, 13, None, None, None, None, None, 70.0, 260.0, 4.0, 390.0, 240.0, 2880.0, 19.0, 10.0, None, None, None, None, None, 7.38, 0.049, 260.0, 4.0, 20.0, 0.06, None, None, 0.63, 20.0, "Dual Threat", "mediocre"),
            ("hist_bust", 2022, "QB", "Bust", 24.0, 80, 4.90, 210.0, 73.0, 29.0, None, None, None, 12, None, None, None, None, None, 38.0, 132.0, 2.0, 360.0, 204.0, 2250.0, 13.0, 11.0, None, None, None, None, None, 6.25, 0.036, 132.0, 2.0, 11.0, 0.02, None, None, 0.56, 80.0, "Dual Threat", "bust"),
        ],
    )
    conn.close()
    csv_path.write_text(
        dedent(
            """\
            player_name,position,expected_draft_ovr,age_at_draft,forty,weight,height,adp
            Future QB,QB,4,21,4.70,220,75,2
            """
        ),
        encoding="utf-8",
    )
    enrichment_path.write_text(
        dedent(
            """\
            player_name,position,forty,vertical,college_games,college_pass_attempts,college_completions,college_passing_yards,college_passing_tds,college_interceptions,college_qb_rush_yards,college_qb_rush_tds,college_scramble_rate
            Future QB,QB,4.55,35,13,430,289,3340,28,6,455,8,0.12
            """
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("fantasy.prospects.pipeline.NflReadPyLoader", _FakeLoader)
    monkeypatch.setattr("fantasy.prospects.pipeline.ProspectModel", _FakeModel)
    monkeypatch.setattr("fantasy.prospects.pipeline.ArchetypeClusterer", _FakeClusterer)
    monkeypatch.setattr("fantasy.prospects.pipeline.CompFinder", _FakeCompFinder)
    monkeypatch.setattr("fantasy.prospects.pipeline.DivergenceEngine", _FakeDivergence)

    result = run_pipeline(
        str(db_path),
        positions=["QB"],
        current_class_year=2026,
        mode="pre_draft",
        pre_draft_csv=str(csv_path),
    )

    conn = duckdb.connect(str(db_path))
    persisted = conn.execute(
        """
        SELECT forty, vertical, college_passing_yards, college_ypa, college_qb_rush_ypg
        FROM historical_prospect_features
        WHERE player_name = 'Future QB' AND draft_year = 2026
        """
    ).fetchone()
    conn.close()

    assert result["prospects_scored"] == 1
    assert persisted is not None
    assert persisted[0] == 4.55
    assert persisted[1] == 35.0
    assert persisted[2] == 3340.0
    assert round(float(persisted[3] or 0.0), 3) == round(3340 / 430, 3)
    assert round(float(persisted[4] or 0.0), 3) == round(455 / 13, 3)

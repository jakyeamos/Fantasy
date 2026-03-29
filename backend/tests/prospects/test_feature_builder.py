from __future__ import annotations

import polars as pl

from fantasy.prospects.feature_builder import FeatureBuilder


def test_feature_builder_builds_features_without_nfl_leakage():
    combine_df = pl.DataFrame(
        [
            {"player_id": "hist_qb", "forty": 4.6, "weight": 220, "height": 75, "vertical": 33},
            {"player_id": "cur_wr", "forty": 4.42, "weight": 205, "height": 72, "vertical": 38},
        ]
    )
    players_df = pl.DataFrame(
        [
            {
                "player_id": "hist_qb",
                "full_name": "History QB",
                "age": 22,
                "games": 13,
                "completions": 286,
                "attempts": 418,
                "passing_yards": 3310,
                "passing_tds": 29,
                "rushing_yards": 442,
                "rushing_tds": 7,
                "scramble_rate": 0.12,
            },
            {
                "player_id": "cur_wr",
                "full_name": "Current WR",
                "age": 21,
                "games": 12,
                "target_share": 0.29,
                "targets": 118,
                "receptions": 74,
                "receiving_yards": 1098,
                "receiving_tds": 11,
                "routes_run": 382,
            },
        ]
    )
    draft_df = pl.DataFrame(
        [
            {"player_id": "hist_qb", "player_name": "History QB", "position": "QB", "season": 2020, "pick": 12},
            {"player_id": "cur_wr", "player_name": "Current WR", "position": "WR", "season": 2026, "pick": 18},
        ]
    )
    weekly_stats_df = pl.DataFrame(
        [
            {"player_id": "hist_qb", "position": "QB", "season": 2020, "week": 1, "fantasy_points": 22.0},
            {"player_id": "hist_qb", "position": "QB", "season": 2021, "week": 1, "fantasy_points": 20.0},
            {"player_id": "hist_qb", "position": "QB", "season": 2022, "week": 1, "fantasy_points": 18.0},
        ]
    )

    builder = FeatureBuilder(
        combine_df=combine_df,
        players_df=players_df,
        draft_df=draft_df,
        weekly_stats_df=weekly_stats_df,
        adp_lookup={"cur_wr": 3.0},
    )
    features = builder.build_all_features(current_class_year=2026)

    assert {item.player_id for item in features} == {"hist_qb", "cur_wr"}
    current = next(item for item in features if item.player_id == "cur_wr")
    history = next(item for item in features if item.player_id == "hist_qb")
    assert current.adp == 3.0
    assert round(float(current.college_rec_ypg or 0.0), 2) == 91.5
    assert round(float(current.college_yprr or 0.0), 3) == round(1098 / 382, 3)
    assert round(float(history.college_completion_pct_proxy or 0.0), 4) == round(286 / 418, 4)
    assert round(float(history.college_qb_rush_ypg or 0.0), 2) == round(442 / 13, 2)
    assert current.outcome_bucket is None
    assert not hasattr(current, "fantasy_points")


def test_feature_builder_build_finish_rank_lookup_orders_by_position_and_season():
    builder = FeatureBuilder(
        combine_df=pl.DataFrame(),
        players_df=pl.DataFrame(),
        draft_df=pl.DataFrame(),
        weekly_stats_df=pl.DataFrame(
            [
                {"player_id": "a", "position": "QB", "season": 2021, "week": 1, "fantasy_points": 20.0},
                {"player_id": "a", "position": "QB", "season": 2021, "week": 2, "fantasy_points": 18.0},
                {"player_id": "b", "position": "QB", "season": 2021, "week": 1, "fantasy_points": 15.0},
                {"player_id": "a", "position": "QB", "season": 2022, "week": 1, "fantasy_points": 10.0},
                {"player_id": "b", "position": "QB", "season": 2022, "week": 1, "fantasy_points": 30.0},
            ]
        ),
    )

    lookup = builder.build_finish_rank_lookup()

    assert lookup["a"] == [1, 2]
    assert lookup["b"] == [2, 1]

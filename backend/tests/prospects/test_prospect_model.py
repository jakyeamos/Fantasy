from __future__ import annotations

import polars as pl

from fantasy.prospects.prospect_model import ProspectModel


def _build_training_frame() -> pl.DataFrame:
    rows = []
    for year in range(2018, 2024):
        rows.extend(
            [
                {
                    "draft_year": year,
                    "age_at_draft": 21.0,
                    "draft_ovr": 5,
                    "forty": 4.45,
                    "weight": 220,
                    "height": 75,
                    "vertical": 36,
                    "college_completion_pct_proxy": 0.69,
                    "college_ypa": 9.1,
                    "college_pass_td_rate": 0.082,
                    "college_qb_rush_ypg": 44.0,
                    "college_scramble_rate": 0.11,
                    "outcome_bucket": "hit",
                },
                {
                    "draft_year": year,
                    "age_at_draft": 22.0,
                    "draft_ovr": 18,
                    "forty": 4.65,
                    "weight": 218,
                    "height": 74,
                    "vertical": 33,
                    "college_completion_pct_proxy": 0.63,
                    "college_ypa": 7.8,
                    "college_pass_td_rate": 0.058,
                    "college_qb_rush_ypg": 24.0,
                    "college_scramble_rate": 0.06,
                    "outcome_bucket": "mediocre",
                },
                {
                    "draft_year": year,
                    "age_at_draft": 24.0,
                    "draft_ovr": 90,
                    "forty": 4.9,
                    "weight": 212,
                    "height": 73,
                    "vertical": 29,
                    "college_completion_pct_proxy": 0.55,
                    "college_ypa": 6.4,
                    "college_pass_td_rate": 0.034,
                    "college_qb_rush_ypg": 10.0,
                    "college_scramble_rate": 0.02,
                    "outcome_bucket": "bust",
                },
            ]
        )
    return pl.DataFrame(rows)


def test_prospect_model_walk_forward_validate_uses_prior_years_only():
    df = _build_training_frame()
    model = ProspectModel("QB")

    result = model.walk_forward_validate(df)

    assert result["sample_size"] > 0
    assert result["per_year"]
    for fold in result["per_year"]:
        assert all(year < fold["test_year"] for year in fold["train_years"])


def test_prospect_model_predicts_probability_distribution_and_importance():
    df = _build_training_frame()
    model = ProspectModel("QB")
    model.train_frame(df)
    X = df.select(model.feature_names).to_numpy()
    y = df["outcome_bucket"].to_numpy()

    predictions = model.predict(X[:2])
    importance = model.get_feature_importance(X, y)

    assert set(predictions[0]) == {"hit", "mediocre", "bust"}
    assert abs(sum(predictions[0].values()) - 1.0) < 1e-6
    assert "draft_ovr" in importance


def test_prospect_model_uses_position_specific_estimators():
    qb_model = ProspectModel("QB")
    rb_model = ProspectModel("RB")

    assert qb_model.model.__class__.__name__ == "LogisticRegression"
    assert rb_model.model.__class__.__name__ == "RandomForestClassifier"


def test_prospect_model_drops_all_null_features_from_active_training_frame():
    df = _build_training_frame().with_columns(pl.lit(None).alias("college_scramble_rate"))
    model = ProspectModel("QB")

    model.train_frame(df)

    assert "college_scramble_rate" not in model.feature_names

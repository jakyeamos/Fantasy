from __future__ import annotations

from fantasy.prospects.archetype_clusterer import ArchetypeClusterer


def test_archetype_clusterer_predicts_labels_and_hit_rates():
    rows = [
        {
            "age_at_draft": 21.0,
            "draft_ovr": 5,
            "forty": 4.4,
            "weight": 205,
            "height": 72,
            "vertical": 38,
            "bench": 10,
            "cone": 6.8,
            "shuttle": 4.1,
            "college_rec_ypg": 90,
            "college_rush_ypg": None,
            "college_mkt_share_proxy": 0.3,
            "college_td_rate": 0.08,
            "college_completion_pct_proxy": None,
            "outcome_bucket": "hit",
        },
        {
            "age_at_draft": 22.0,
            "draft_ovr": 22,
            "forty": 4.5,
            "weight": 210,
            "height": 73,
            "vertical": 35,
            "bench": 11,
            "cone": 6.9,
            "shuttle": 4.2,
            "college_rec_ypg": 75,
            "college_rush_ypg": None,
            "college_mkt_share_proxy": 0.24,
            "college_td_rate": 0.06,
            "college_completion_pct_proxy": None,
            "outcome_bucket": "mediocre",
        },
        {
            "age_at_draft": 23.0,
            "draft_ovr": 85,
            "forty": 4.62,
            "weight": 198,
            "height": 71,
            "vertical": 31,
            "bench": 8,
            "cone": 7.2,
            "shuttle": 4.4,
            "college_rec_ypg": 48,
            "college_rush_ypg": None,
            "college_mkt_share_proxy": 0.15,
            "college_td_rate": 0.03,
            "college_completion_pct_proxy": None,
            "outcome_bucket": "bust",
        },
        {
            "age_at_draft": 21.5,
            "draft_ovr": 18,
            "forty": 4.47,
            "weight": 207,
            "height": 73,
            "vertical": 37,
            "bench": 9,
            "cone": 6.85,
            "shuttle": 4.15,
            "college_rec_ypg": 86,
            "college_rush_ypg": None,
            "college_mkt_share_proxy": 0.29,
            "college_td_rate": 0.07,
            "college_completion_pct_proxy": None,
            "outcome_bucket": "hit",
        },
    ]
    clusterer = ArchetypeClusterer("WR")
    clusterer.fit(rows)

    labels = clusterer.predict(rows[:2])
    rates = clusterer.get_archetype_hit_rates(
        [{**row, "archetype_label": label} for row, label in zip(rows, clusterer.predict(rows), strict=False)]
    )

    assert len(labels) == 2
    assert all(isinstance(label, str) and label for label in labels)
    assert rates

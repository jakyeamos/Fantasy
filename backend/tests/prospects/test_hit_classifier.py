from __future__ import annotations

from fantasy.prospects.constants import OUTCOME_BUST, OUTCOME_HIT, OUTCOME_MEDIOCRE
from fantasy.prospects.hit_classifier import HitClassifier


def test_hit_classifier_assigns_three_outcomes():
    classifier = HitClassifier()

    assert classifier.classify_player("QB", [3, 5, 10, 12]) == OUTCOME_HIT
    assert classifier.classify_player("QB", [4, 15, 20, 18]) == OUTCOME_MEDIOCRE
    assert classifier.classify_player("QB", [15, 18, 22, 20]) == OUTCOME_BUST


def test_hit_classifier_requires_minimum_outcome_seasons():
    classifier = HitClassifier()

    assert classifier.classify_player("RB", [10, 12]) is None


def test_hit_classifier_classify_cohort_sets_outcome_bucket():
    classifier = HitClassifier()

    rows = classifier.classify_cohort(
        [
            {"player_id": "a", "position": "WR", "season_finish_ranks": [12, 20, 50, 40]},
            {"player_id": "b", "position": "WR", "season_finish_ranks": [50, 55, 60, 65]},
        ]
    )

    assert rows[0]["outcome_bucket"] == OUTCOME_HIT
    assert rows[1]["outcome_bucket"] == OUTCOME_BUST

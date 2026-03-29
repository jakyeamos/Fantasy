from __future__ import annotations

from fantasy.prospects.constants import (
    HIT_THRESHOLDS,
    MEDIOCRE_THRESHOLDS,
    MIN_OUTCOME_SEASONS,
    OUTCOME_BUST,
    OUTCOME_HIT,
    OUTCOME_MEDIOCRE,
)


class HitClassifier:
    def classify_player(self, position: str, season_finish_ranks: list[int]) -> str | None:
        if len(season_finish_ranks) < MIN_OUTCOME_SEASONS:
            return None

        hit_cfg = HIT_THRESHOLDS[position]
        window = season_finish_ranks[: hit_cfg["window"]]
        hit_count = sum(1 for rank in window if rank <= hit_cfg["top_n"])
        if hit_count >= hit_cfg["min_seasons"]:
            return OUTCOME_HIT

        med_cfg = MEDIOCRE_THRESHOLDS[position]
        med_window = season_finish_ranks[: med_cfg["window"]]
        med_count = sum(1 for rank in med_window if rank <= med_cfg["top_n"])
        if med_count >= med_cfg["min_seasons"]:
            return OUTCOME_MEDIOCRE

        return OUTCOME_BUST

    def classify_cohort(self, features_with_ranks: list[dict]) -> list[dict]:
        classified: list[dict] = []
        for item in features_with_ranks:
            row = dict(item)
            row["outcome_bucket"] = self.classify_player(
                str(row["position"]),
                list(row.get("season_finish_ranks", [])),
            )
            classified.append(row)
        return classified

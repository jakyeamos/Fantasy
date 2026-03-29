from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

from fantasy.prospects.constants import (
    CLUSTER_FEATURES,
    DRAFT_CAPITAL_TIERS,
    FEATURE_DISPLAY_NAMES,
    MIN_COMP_COUNT,
    OUTCOME_BUST,
    OUTCOME_HIT,
    OUTCOME_MEDIOCRE,
)
from fantasy.prospects.models import HistoricalComp, ProspectFeatures

try:
    from scipy.spatial.distance import cdist
except ModuleNotFoundError:  # pragma: no cover - exercised only when optional deps missing
    def cdist(a: np.ndarray, b: np.ndarray, metric: str = "euclidean") -> np.ndarray:
        if metric != "euclidean":
            raise ValueError("Fallback cdist only supports euclidean distance")
        return np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(axis=2))


class CompFinder:
    def __init__(self):
        self.scaler = StandardScaler()
        self.imputer = SimpleImputer(strategy="median")

    def get_draft_capital_tier(self, draft_ovr: int | None) -> str:
        if draft_ovr is None:
            return "Day 3"
        for tier_name, (lo, hi) in DRAFT_CAPITAL_TIERS.items():
            if lo <= draft_ovr <= hi:
                return tier_name
        return "Day 3"

    def find_comps(
        self,
        prospect: ProspectFeatures,
        historical_pool: list[ProspectFeatures],
        feature_names: list[str] | None = None,
    ) -> tuple[list[HistoricalComp], bool]:
        tier = self.get_draft_capital_tier(prospect.draft_ovr)
        filtered = [
            candidate
            for candidate in historical_pool
            if candidate.player_id != prospect.player_id
            and candidate.position == prospect.position
            and self.get_draft_capital_tier(candidate.draft_ovr) == tier
            and candidate.outcome_bucket in {OUTCOME_HIT, OUTCOME_MEDIOCRE, OUTCOME_BUST}
        ]
        if not filtered:
            return [], True
        names = self._resolve_feature_names(
            prospect,
            filtered,
            feature_names or CLUSTER_FEATURES,
        )

        matrix = np.array([[self._numeric(getattr(row, name)) for name in names] for row in filtered], dtype=float)
        prospect_vec = np.array([[self._numeric(getattr(prospect, name)) for name in names]], dtype=float)
        matrix = self.imputer.fit_transform(matrix)
        prospect_vec = self.imputer.transform(prospect_vec)
        matrix = self.scaler.fit_transform(matrix)
        prospect_vec = self.scaler.transform(prospect_vec)
        distances = cdist(prospect_vec, matrix, metric="euclidean")[0]

        comps: list[HistoricalComp] = []
        for role, bucket in [
            ("ceiling", OUTCOME_HIT),
            ("median", OUTCOME_MEDIOCRE),
            ("floor", OUTCOME_BUST),
        ]:
            nearest = self._nearest_for_bucket(filtered, distances, bucket)
            if nearest is None:
                continue
            candidate, index = nearest
            comp_vec = matrix[index]
            feature_contributors = self._compute_feature_contributions(
                prospect_vec[0],
                comp_vec,
                names,
            )
            comps.append(
                HistoricalComp(
                    player_id=candidate.player_id,
                    player_name=candidate.player_name,
                    role=role,
                    outcome_bucket=bucket,
                    match_reason=f"similar {', '.join(feature_contributors)} profile",
                )
            )
        return comps, len(filtered) < MIN_COMP_COUNT

    def _nearest_for_bucket(
        self,
        candidates: list[ProspectFeatures],
        distances: np.ndarray,
        bucket: str,
    ) -> tuple[ProspectFeatures, int] | None:
        best: tuple[ProspectFeatures, int] | None = None
        best_distance = float("inf")
        for index, candidate in enumerate(candidates):
            if candidate.outcome_bucket != bucket:
                continue
            if distances[index] < best_distance:
                best_distance = float(distances[index])
                best = (candidate, index)
        return best

    def _compute_feature_contributions(
        self,
        prospect_vec: np.ndarray,
        comp_vec: np.ndarray,
        feature_names: list[str],
    ) -> list[str]:
        deltas = np.abs(prospect_vec - comp_vec)
        indices = np.argsort(deltas)[:3]
        labels = []
        for index in indices:
            label = FEATURE_DISPLAY_NAMES.get(feature_names[int(index)], feature_names[int(index)])
            if label not in labels:
                labels.append(label)
        return labels[:3]

    def _numeric(self, value: Any) -> float:
        if value in (None, ""):
            return np.nan
        try:
            return float(value)
        except (TypeError, ValueError):
            return np.nan

    def _resolve_feature_names(
        self,
        prospect: ProspectFeatures,
        historical_pool: list[ProspectFeatures],
        candidate_names: list[str],
    ) -> list[str]:
        observed: list[str] = []
        for name in candidate_names:
            if not hasattr(prospect, name):
                continue
            values = [self._numeric(getattr(prospect, name))]
            values.extend(self._numeric(getattr(candidate, name)) for candidate in historical_pool)
            if any(not np.isnan(value) for value in values):
                observed.append(name)
        return observed or [name for name in candidate_names if hasattr(prospect, name)]

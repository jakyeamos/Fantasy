from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

import numpy as np

from fantasy.prospects.constants import (
    ARCHETYPE_LABELS,
    CLUSTER_FEATURES,
    CLUSTER_RANDOM_STATE,
    OUTCOME_BUCKETS,
    POSITION_CLUSTER_COUNT,
)

try:
    from sklearn.cluster import KMeans
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler
except ModuleNotFoundError:  # pragma: no cover - exercised only when optional deps missing
    KMeans = None
    SimpleImputer = None
    StandardScaler = None


def _require_sklearn() -> None:
    if None in {KMeans, SimpleImputer, StandardScaler}:
        raise RuntimeError(
            "Phase 8 clustering dependencies are missing. Install scikit-learn to run archetype clustering."
        )


class ArchetypeClusterer:
    def __init__(self, position: str):
        _require_sklearn()
        self.position = position
        self.feature_names = list(CLUSTER_FEATURES)
        self.scaler = StandardScaler()
        self.imputer = SimpleImputer(strategy="median")
        self.cluster_count = POSITION_CLUSTER_COUNT[position]
        self.model = KMeans(
            n_clusters=self.cluster_count,
            random_state=CLUSTER_RANDOM_STATE,
            n_init=10,
        )
        self.cluster_label_map: dict[int, str] = {}

    def fit(self, rows: list[dict[str, Any]]) -> None:
        self.feature_names = self._resolve_feature_names(rows)
        X = self._matrix(rows)
        X_imputed = self.imputer.fit_transform(X)
        X_scaled = self.scaler.fit_transform(X_imputed)
        self.model.fit(X_scaled)
        labels = ARCHETYPE_LABELS[self.position]
        self.cluster_label_map = {
            cluster_id: labels[cluster_id % len(labels)]
            for cluster_id in range(self.cluster_count)
        }

    def predict(self, rows: list[dict[str, Any]]) -> list[str]:
        if not rows:
            return []
        X = self._matrix(rows)
        X_imputed = self.imputer.transform(X)
        X_scaled = self.scaler.transform(X_imputed)
        cluster_ids = self.model.predict(X_scaled)
        return [self.cluster_label_map[int(cluster_id)] for cluster_id in cluster_ids]

    def get_archetype_hit_rates(self, rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
        if not rows:
            return {}
        rates: dict[str, Counter[str]] = defaultdict(Counter)
        for row in rows:
            archetype = str(row.get("archetype_label") or "Unknown")
            outcome = str(row.get("outcome_bucket") or "")
            if outcome in OUTCOME_BUCKETS:
                rates[archetype][outcome] += 1
        distribution: dict[str, dict[str, float]] = {}
        for archetype, counts in rates.items():
            total = sum(counts.values()) or 1
            distribution[archetype] = {
                bucket: counts.get(bucket, 0) / total for bucket in OUTCOME_BUCKETS
            }
        return distribution

    def _matrix(self, rows: list[dict[str, Any]]) -> np.ndarray:
        matrix: list[list[float | None]] = []
        for row in rows:
            matrix.append([self._coerce_numeric(row.get(name)) for name in self.feature_names])
        return np.array(matrix, dtype=float)

    def _resolve_feature_names(self, rows: list[dict[str, Any]]) -> list[str]:
        if not rows:
            return list(CLUSTER_FEATURES)
        observed: list[str] = []
        for name in CLUSTER_FEATURES:
            values = [self._coerce_numeric(row.get(name)) for row in rows]
            if any(not np.isnan(value) for value in values):
                observed.append(name)
        return observed or list(CLUSTER_FEATURES)

    def _coerce_numeric(self, value: Any) -> float:
        if value in (None, ""):
            return np.nan
        try:
            return float(value)
        except (TypeError, ValueError):
            return np.nan

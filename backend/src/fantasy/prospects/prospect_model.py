from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import polars as pl

from fantasy.prospects.constants import OUTCOME_BUCKETS, POSITION_FEATURES

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.impute import SimpleImputer
    from sklearn.inspection import permutation_importance
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
except ModuleNotFoundError:  # pragma: no cover - exercised only when optional deps missing
    RandomForestClassifier = None
    SimpleImputer = None
    permutation_importance = None
    LogisticRegression = None
    StandardScaler = None


def _require_sklearn() -> None:
    if None in {
        RandomForestClassifier,
        SimpleImputer,
        permutation_importance,
        LogisticRegression,
        StandardScaler,
    }:
        raise RuntimeError(
            "Phase 8 model dependencies are missing. Install scikit-learn to run prospect models."
        )


@dataclass
class ValidationFold:
    train_years: list[int]
    test_year: int
    accuracy: float | None
    sample_size: int


class ProspectModel:
    def __init__(self, position: str):
        _require_sklearn()
        self.position = position
        self.base_feature_names = list(POSITION_FEATURES[position])
        self.feature_names = list(self.base_feature_names)
        self.imputer = SimpleImputer(strategy="median")
        self.scaler = StandardScaler()
        self._class_order = list(OUTCOME_BUCKETS)
        self.model = self._build_estimator()

    def walk_forward_validate(self, features_df: pl.DataFrame) -> dict[str, Any]:
        if features_df.is_empty():
            return {"overall_accuracy": None, "per_year": [], "sample_size": 0}

        folds: list[ValidationFold] = []
        years = sorted(features_df["draft_year"].unique().to_list())
        total_correct = 0
        total_count = 0

        for index, test_year in enumerate(years):
            train_years = years[:index]
            if len(train_years) < 3:
                continue

            train_df = features_df.filter(pl.col("draft_year").is_in(train_years))
            test_df = features_df.filter(pl.col("draft_year") == test_year)
            feature_names = self.resolve_feature_names(train_df)
            X_train, y_train = self._extract_xy(train_df, feature_names)
            X_test, y_test = self._extract_xy(test_df, feature_names)
            if X_train.size == 0 or X_test.size == 0 or len(set(y_train.tolist())) < 2:
                folds.append(
                    ValidationFold(
                        train_years=train_years,
                        test_year=test_year,
                        accuracy=None,
                        sample_size=len(y_test),
                    )
                )
                continue

            imputer = SimpleImputer(strategy="median")
            scaler = StandardScaler()
            model = self._build_estimator()
            X_train_imputed = imputer.fit_transform(X_train)
            X_train_scaled = scaler.fit_transform(X_train_imputed)
            model.fit(X_train_scaled, y_train)
            X_test_imputed = imputer.transform(X_test)
            X_test_scaled = scaler.transform(X_test_imputed)
            predictions = model.predict(X_test_scaled)
            correct = int(np.sum(predictions == y_test))
            total_correct += correct
            total_count += len(y_test)
            folds.append(
                ValidationFold(
                    train_years=train_years,
                    test_year=test_year,
                    accuracy=correct / len(y_test) if len(y_test) else None,
                    sample_size=len(y_test),
                )
            )

        return {
            "overall_accuracy": (total_correct / total_count) if total_count else None,
            "per_year": [
                {
                    "train_years": fold.train_years,
                    "test_year": fold.test_year,
                    "accuracy": fold.accuracy,
                    "sample_size": fold.sample_size,
                }
                for fold in folds
            ],
            "sample_size": total_count,
        }

    def resolve_feature_names(self, df: pl.DataFrame) -> list[str]:
        available = [name for name in self.base_feature_names if name in df.columns]
        observed: list[str] = []
        for name in available:
            values = df.get_column(name).to_list()
            if any(value is not None and not np.isnan(value) for value in values):
                observed.append(name)
        return observed or available or list(self.base_feature_names)

    def train_frame(self, df: pl.DataFrame) -> None:
        self.feature_names = self.resolve_feature_names(df)
        self.imputer = SimpleImputer(strategy="median")
        self.scaler = StandardScaler()
        self.model = self._build_estimator()
        X, y = self._extract_xy(df, self.feature_names)
        self.train(X, y)

    def predict_frame(self, df: pl.DataFrame) -> list[dict[str, float]]:
        X = df.select(self.feature_names).fill_nan(None).to_numpy()
        return self.predict(X)

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        X_imputed = self.imputer.fit_transform(X)
        X_scaled = self.scaler.fit_transform(X_imputed)
        self.model.fit(X_scaled, y)

    def predict(self, X: np.ndarray) -> list[dict[str, float]]:
        X_imputed = self.imputer.transform(X)
        X_scaled = self.scaler.transform(X_imputed)
        probs = self.model.predict_proba(X_scaled)
        classes = list(self.model.classes_)
        outputs: list[dict[str, float]] = []
        for row in probs:
            mapped = {label: 0.0 for label in self._class_order}
            for index, cls in enumerate(classes):
                mapped[str(cls)] = float(row[index])
            outputs.append(mapped)
        return outputs

    def get_feature_importance(self, X_val: np.ndarray, y_val: np.ndarray) -> dict[str, float]:
        if len(y_val) == 0:
            return {name: 0.0 for name in self.feature_names}
        X_imputed = self.imputer.transform(X_val)
        X_scaled = self.scaler.transform(X_imputed)
        result = permutation_importance(
            self.model,
            X_scaled,
            y_val,
            n_repeats=30,
            random_state=42,
        )
        return {
            name: float(score)
            for name, score in zip(self.feature_names, result.importances_mean, strict=False)
        }

    def _extract_xy(
        self,
        df: pl.DataFrame,
        feature_names: list[str] | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        names = feature_names or self.feature_names
        X = df.select(names).fill_nan(None).to_numpy()
        y = np.array(df["outcome_bucket"].to_list(), dtype=object)
        return X, y

    def _predict_labels(self, X: np.ndarray) -> np.ndarray:
        X_imputed = self.imputer.transform(X)
        X_scaled = self.scaler.transform(X_imputed)
        return self.model.predict(X_scaled)

    def _build_estimator(self):
        if self.position == "QB":
            return LogisticRegression(
                C=0.1,
                max_iter=1000,
                random_state=42,
            )
        return RandomForestClassifier(
            n_estimators=200,
            max_features="sqrt",
            random_state=42,
        )

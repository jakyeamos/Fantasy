from __future__ import annotations

from statistics import median

from fantasy.prospects.constants import FEATURE_DISPLAY_NAMES, SUB_FLAG_FEATURES
from fantasy.prospects.models import ProspectFeatures, SubFlag


class DivergenceEngine:
    def compute_divergence(
        self,
        player_id: str,
        model_rankings: list[str],
        adp_rankings: list[str],
        low_confidence: bool,
    ) -> tuple[str | None, int | None]:
        if low_confidence:
            return None, None
        try:
            model_rank = model_rankings.index(player_id) + 1
            adp_rank = adp_rankings.index(player_id) + 1
        except ValueError:
            return None, None
        delta = adp_rank - model_rank
        if abs(delta) < 2:
            return None, None
        return ("undervalued" if delta > 0 else "overvalued", abs(delta))

    def compute_sub_flags(
        self,
        prospect: ProspectFeatures,
        comp_features: list[ProspectFeatures],
    ) -> list[SubFlag]:
        if not comp_features:
            return []
        flags: list[SubFlag] = []
        for signal_name, (feature_name, lower_is_better) in SUB_FLAG_FEATURES.items():
            player_value = getattr(prospect, feature_name, None)
            pool = [getattr(comp, feature_name, None) for comp in comp_features]
            values = [float(value) for value in pool if value is not None]
            if player_value is None or not values:
                continue
            baseline = median(values)
            delta = float(player_value) - baseline
            if abs(delta) < 0.01:
                direction = "neutral"
            else:
                positive = delta < 0 if lower_is_better else delta > 0
                direction = "positive" if positive else "negative"
            label = FEATURE_DISPLAY_NAMES.get(feature_name, signal_name.lower())
            magnitude = round(abs(delta), 2)
            comparator = "better" if direction == "positive" else "worse"
            if direction == "neutral":
                text = f"near the historical median {label}"
            else:
                text = f"{magnitude} from median {label} - {comparator}"
            flags.append(
                SubFlag(
                    signal_name=signal_name,
                    direction=direction,
                    magnitude_str=text,
                )
            )
        return flags

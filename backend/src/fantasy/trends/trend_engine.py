from __future__ import annotations

from typing import Any, Sequence

import duckdb

from fantasy.intelligence.constants import POSITIONAL_CLIFF_AGE, POSITIONAL_PEAK_AGE
from fantasy.intelligence.valuation_engine import ValuationEngine, _clamp01
from fantasy.trends.constants import COMPONENT_COLS, COMPONENT_WEIGHTS, GENERIC_FORMAT_ROW, TREND_THRESHOLD
from fantasy.trends.models import TrendResult
from fantasy.trends.trend_repo import TrendRepo


class TrendEngine:
    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        repo: TrendRepo | None = None,
    ) -> None:
        self._conn = conn
        self._repo = repo or TrendRepo(conn)
        self._valuation = ValuationEngine(conn)

    def current_snapshot(self, player_id: str) -> dict[str, Any] | None:
        latest = self._repo.get_latest_player_row(player_id)
        if latest is not None:
            return latest
        baseline = self._repo.get_player_baseline(player_id)
        if baseline is None:
            return None
        if baseline["startup_adp"] is None and baseline["ppg"] is None:
            return None
        return self._build_snapshot_from_baseline(baseline)

    def current_snapshots(self, player_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
        ids = [str(player_id) for player_id in player_ids]
        if not ids:
            return {}

        snapshots = self._repo.get_latest_player_rows(ids)
        missing_ids = [player_id for player_id in ids if player_id not in snapshots]
        baselines = self._repo.get_player_baselines(missing_ids)
        for player_id, baseline in baselines.items():
            if baseline["startup_adp"] is None and baseline["ppg"] is None:
                continue
            snapshots[player_id] = self._build_snapshot_from_baseline(baseline)
        return snapshots

    def compute_trend(self, player_id: str) -> TrendResult:
        seasons = self._repo.get_player_seasons(player_id, limit=2)
        if len(seasons) >= 2:
            return self._compute_from_two_seasons(
                player_id,
                self._enrich_snapshot_meta(player_id, seasons[0]),
                self._enrich_snapshot_meta(player_id, seasons[1]),
                seasons_compared=2,
            )
        if len(seasons) == 1:
            current = self._enrich_snapshot_meta(player_id, seasons[0])
            return self._backfill_single_season(player_id, current)
        return self._backfill_no_history(player_id)

    def compute_all_players(
        self, player_ids: Sequence[str] | None = None
    ) -> dict[str, TrendResult]:
        ids = list(player_ids) if player_ids is not None else [
            candidate["player_id"] for candidate in self._repo.list_candidate_players()
        ]
        return {player_id: self.compute_trend(player_id) for player_id in ids}

    def compute_trends(
        self,
        player_ids: Sequence[str],
        *,
        snapshots: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, TrendResult]:
        ids = [str(player_id) for player_id in player_ids]
        if not ids:
            return {}

        current_snapshots = snapshots if snapshots is not None else self.current_snapshots(ids)
        seasons_by_player = self._repo.get_player_seasons_map(ids, limit=2)
        trends: dict[str, TrendResult] = {}
        for player_id in ids:
            seasons = seasons_by_player.get(player_id, [])
            if len(seasons) >= 2:
                trends[player_id] = self._compute_from_two_seasons(
                    player_id,
                    seasons[0],
                    seasons[1],
                    seasons_compared=2,
                )
                continue

            current = current_snapshots.get(player_id)
            if len(seasons) == 1:
                trends[player_id] = self._backfill_single_season(
                    player_id,
                    current or seasons[0],
                )
                continue

            if current is None:
                trends[player_id] = TrendResult(
                    player_id=player_id,
                    trend_label="will_maintain",
                    confidence="LOW",
                    delta_magnitude=0.0,
                    component_deltas={},
                    adp_delta=None,
                    seasons_compared=0,
                    backfilled=True,
                )
                continue

            prior = self._proxy_prior_from_snapshot(current)
            result = self._compute_from_two_seasons(
                player_id,
                current,
                prior,
                seasons_compared=1,
            )
            result.backfilled = True
            result.confidence = "LOW"
            trends[player_id] = result
        return trends

    def _compute_from_two_seasons(
        self,
        player_id: str,
        current: dict[str, Any],
        prior: dict[str, Any],
        *,
        seasons_compared: int,
    ) -> TrendResult:
        component_deltas: dict[str, float] = {}
        weighted_total = 0.0
        weight_sum = 0.0
        for component, weight in COMPONENT_WEIGHTS.items():
            current_value = float(current.get(component) or 0.0)
            prior_value = float(prior.get(component) or 0.0)
            delta = current_value - prior_value
            component_deltas[component] = round(delta, 4)
            weighted_total += delta * weight
            weight_sum += abs(weight)

        delta_magnitude = weighted_total / max(weight_sum, 1e-9)
        adp_delta = self._adp_delta(current.get("startup_adp"), prior.get("startup_adp"))
        confidence = self._confidence_from_history(current, prior, component_deltas)
        backfilled = bool(current.get("backfilled")) or bool(prior.get("backfilled"))
        result = TrendResult(
            player_id=player_id,
            trend_label=self._label_for_delta(delta_magnitude),
            confidence=confidence,
            delta_magnitude=round(delta_magnitude, 4),
            component_deltas=component_deltas,
            adp_delta=round(adp_delta, 4) if adp_delta is not None else None,
            seasons_compared=seasons_compared,
            backfilled=backfilled,
        )
        return result

    def _backfill_single_season(self, player_id: str, current: dict[str, Any]) -> TrendResult:
        prior = self._proxy_prior_from_snapshot(current)
        result = self._compute_from_two_seasons(
            player_id,
            current,
            prior,
            seasons_compared=1,
        )
        result.backfilled = True
        result.confidence = "LOW"
        return result

    def _backfill_no_history(self, player_id: str) -> TrendResult:
        current = self.current_snapshot(player_id)
        if current is None:
            return TrendResult(
                player_id=player_id,
                trend_label="will_maintain",
                confidence="LOW",
                delta_magnitude=0.0,
                component_deltas={},
                adp_delta=None,
                seasons_compared=0,
                backfilled=True,
            )
        prior = self._proxy_prior_from_snapshot(current)
        result = self._compute_from_two_seasons(
            player_id,
            current,
            prior,
            seasons_compared=1,
        )
        result.backfilled = True
        result.confidence = "LOW"
        return result

    def _enrich_snapshot_meta(
        self, player_id: str, snapshot: dict[str, Any]
    ) -> dict[str, Any]:
        meta = self._repo.get_player_baseline(player_id) or {}
        enriched = dict(snapshot)
        enriched.setdefault("player_id", player_id)
        enriched.setdefault("full_name", meta.get("full_name", player_id))
        enriched.setdefault("position", meta.get("position", "UNKNOWN"))
        enriched.setdefault("age", meta.get("age", 24))
        return enriched

    def _build_snapshot_from_baseline(self, baseline: dict[str, Any]) -> dict[str, Any]:
        position = str(baseline.get("position") or "UNKNOWN")
        age = int(baseline.get("age") or 24)
        ppg = baseline.get("ppg")
        games_played = int(baseline.get("games_played") or 0)
        best_week = baseline.get("best_week")
        startup_adp = baseline.get("startup_adp")

        current_production = self._valuation._production_score(
            ppg,
            position,
            GENERIC_FORMAT_ROW,
        )
        role_stability = _clamp01(games_played / 17.0) if games_played else 0.45
        short_term = _clamp01(0.7 * current_production + 0.3 * role_stability)
        age_curve = self._valuation._age_curve_score(position, age)
        fragility = _clamp01(1.0 - role_stability)
        market_liquidity = _clamp01(1.0 - min(startup_adp or 200.0, 250.0) / 250.0)
        positional_scarcity = self._valuation._positional_scarcity(
            position,
            GENERIC_FORMAT_ROW,
        )
        ceiling = _clamp01(((best_week if best_week is not None else (ppg or 10.0)) / 30.0))
        floor = _clamp01(((ppg if ppg is not None else 8.0) / 20.0) * max(role_stability, 0.5))
        rerollability = self._valuation._rerollability(position, age)
        contract = _clamp01(0.6 * age_curve + 0.4 * role_stability)
        insulation = _clamp01((role_stability + age_curve + (1.0 - fragility)) / 3.0)
        return {
            "player_id": str(baseline.get("player_id")),
            "full_name": str(baseline.get("full_name") or baseline.get("player_id")),
            "position": position,
            "age": age,
            "season": None,
            "startup_adp": startup_adp,
            "backfilled": True,
            "comp_current_production": current_production,
            "comp_short_term": short_term,
            "comp_role_stability": role_stability,
            "comp_age_curve": age_curve,
            "comp_insulation": insulation,
            "comp_market_liquidity": market_liquidity,
            "comp_positional_scarcity": positional_scarcity,
            "comp_fragility": fragility,
            "comp_ceiling": ceiling,
            "comp_floor": floor,
            "comp_rerollability": rerollability,
            "comp_contract": contract,
        }

    def _proxy_prior_from_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        position = str(snapshot.get("position") or "UNKNOWN")
        age = int(snapshot.get("age") or 24)
        quality = (
            float(snapshot.get("comp_short_term") or 0.0)
            + float(snapshot.get("comp_current_production") or 0.0)
            + float(snapshot.get("comp_role_stability") or 0.0)
            + float(snapshot.get("comp_ceiling") or 0.0)
            + float(snapshot.get("comp_floor") or 0.0)
            + float(snapshot.get("comp_insulation") or 0.0)
        ) / 6.0
        fragility = float(snapshot.get("comp_fragility") or 0.5)
        bias = (quality - 0.5) * 0.25 + (0.5 - fragility) * 0.12
        if age <= 23:
            bias += 0.10
        if age >= POSITIONAL_CLIFF_AGE.get(position, 31):
            bias -= 0.12
        elif age >= POSITIONAL_PEAK_AGE.get(position, 28) + 1:
            bias -= 0.06
        bias = max(-0.22, min(0.22, bias))

        prior = dict(snapshot)
        for component in COMPONENT_COLS:
            current_value = float(snapshot.get(component) or 0.0)
            if component == "comp_fragility":
                prior[component] = _clamp01(current_value + bias)
            else:
                prior[component] = _clamp01(current_value - bias)
        startup_adp = snapshot.get("startup_adp")
        if startup_adp is not None:
            prior["startup_adp"] = max(1.0, min(250.0, float(startup_adp) + bias * 40.0))
        prior["backfilled"] = True
        return prior

    def _confidence_from_history(
        self,
        current: dict[str, Any],
        prior: dict[str, Any],
        component_deltas: dict[str, float],
    ) -> str:
        if current.get("backfilled") or prior.get("backfilled"):
            return "LOW"

        significant = [
            1 if delta > 0.03 else -1 if delta < -0.03 else 0
            for delta in component_deltas.values()
        ]
        non_zero = [direction for direction in significant if direction != 0]
        if not non_zero:
            return "MEDIUM"
        agreement = max(non_zero.count(1), non_zero.count(-1)) / len(non_zero)
        if agreement >= 0.75:
            return "HIGH"
        if agreement >= 0.55:
            return "MEDIUM"
        return "LOW"

    def _label_for_delta(self, delta: float) -> str:
        if delta > TREND_THRESHOLD:
            return "will_rise"
        if delta < -TREND_THRESHOLD:
            return "will_fall"
        return "will_maintain"

    def _adp_delta(
        self, current_adp: float | None, prior_adp: float | None
    ) -> float | None:
        if current_adp is None or prior_adp is None:
            return None
        return float(prior_adp) - float(current_adp)

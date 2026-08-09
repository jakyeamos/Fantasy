"""Build the complete, evidence-aware Trade Lab analysis packet."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal

import duckdb

from fantasy.data_health import assess_stats_health
from fantasy.decision.calibration import calibration_evidence
from fantasy.intelligence.models import ScorecardInputs
from fantasy.intelligence.scorecard_engine import ScorecardEngine
from fantasy.lineup.lineup_engine import LineupEngine
from fantasy.lineup.models import LineupResult
from fantasy.trade.constants import DIMENSION_WEIGHTS
from fantasy.trade.models import (
    DimensionScore,
    PackageBuilderResult,
    PackageOffer,
    TradeAnalysis,
    TradeAnalysisAsset,
    TradeAnalysisOffer,
    TradeAnalysisScenario,
    TradeAnalysisQuality,
    TradeAsset,
    TradeEvaluation,
    TradeLineupImpact,
    TradeNegotiationLadder,
    TradeRequest,
)
from fantasy.trade.trade_repo import TradeRepo


_DIMENSION_NAMES = tuple(DIMENSION_WEIGHTS)
_STALE_AFTER_HOURS = 72.0
_ACCEPT_THRESHOLD = 60.0
_COUNTER_THRESHOLD = 50.0
_HOLD_THRESHOLD = 42.0
_OFFER_PURPOSE = Literal[
    "current",
    "aggressive_open",
    "preferred_close",
    "fallback",
    "walk_away",
]


def _safe_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def _asset_key(asset: TradeAsset) -> tuple[object, ...]:
    return (
        asset.asset_type,
        asset.player_id,
        asset.pick_owner_roster_id,
        asset.pick_year,
        asset.pick_round,
        asset.projected_slot,
    )


def _asset_context_value(value: dict[str, Any]) -> float | None:
    market = _optional_float(value.get("lens_market"))
    if market is None:
        return None

    def lens(key: str) -> float:
        return _safe_float(value.get(key), market)

    return (
        market * 0.35
        + lens("lens_team_fit") * 0.20
        + lens("lens_direction") * 0.15
        + lens("lens_insulation") * 0.12
        + lens("lens_production") * 0.08
        + lens("comp_positional_scarcity") * 0.06
        + lens("comp_market_liquidity") * 0.04
    )


def _parse_timestamp(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value).strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _display_verdict(verdict: str) -> str:
    return verdict.replace("_", " ").title()


def _score_verdict(score: float) -> str:
    if score >= _ACCEPT_THRESHOLD:
        return "accept"
    if score >= _COUNTER_THRESHOLD:
        return "counter"
    if score >= _HOLD_THRESHOLD:
        return "hold"
    return "walk_away"


class TradeAnalysisBuilder:
    """Compose a Trade Lab packet without mutating league state."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._repo = TradeRepo(conn)
        self._roster_names: dict[int, str] = {}
        self._player_owners: dict[str, int] = {}
        self._player_catalog: dict[str, dict[str, object]] = {}
        self._player_values: dict[str, dict[str, Any]] = {}
        self._pick_inventory: list[dict[str, Any]] = []
        self._asset_cache: dict[tuple[object, ...], TradeAnalysisAsset] = {}

    def build(
        self,
        request: TradeRequest,
        evaluation: TradeEvaluation,
    ) -> TradeAnalysis:
        freshness, league_season = self._freshness(request.league_id)
        stats_health = self._stats_health(league_season)
        calibration = self._calibration()
        self._load_context(request)

        assets = self._build_assets(request)
        lineup_impacts, lineup_available = self._build_lineup_impacts(
            request,
            stats_health,
            freshness,
        )
        scenarios, offers = self._build_scenarios(
            request,
            evaluation,
            assets,
            lineup_impacts,
            stats_health,
            freshness,
            calibration,
        )

        gates = self._build_gates(
            request,
            assets,
            evaluation,
            lineup_available,
            scenarios,
            offers,
            calibration,
        )
        quality = self._build_quality(
            gates,
            assets,
            lineup_impacts,
            freshness,
            stats_health,
            calibration,
            evaluation,
        )

        point = self._score_evaluation(evaluation)
        score_low, score_high = self._score_band(
            point,
            assets,
            lineup_impacts,
            freshness,
            stats_health,
            calibration,
            evaluation,
        )
        verdict = _score_verdict(point)
        if quality.status == "blocked" and verdict == "accept":
            verdict = "hold"

        key_reasons = self._key_reasons(evaluation)
        user_impact = next(
            (
                impact
                for impact in lineup_impacts
                if impact.roster_id == request.user_roster_id
            ),
            None,
        )
        if user_impact and user_impact.score_delta is not None:
            direction = "improves" if user_impact.score_delta > 0 else "reduces"
            key_reasons.append(
                f"The projected lineup {direction} by {abs(user_impact.score_delta):.2f} score points "
                f"({user_impact.before_title_window} to {user_impact.after_title_window})."
            )

        contrary_case = self._contrary_case(evaluation)
        what_changes = self._what_changes_the_answer(
            request,
            assets,
            freshness,
            stats_health,
            calibration,
        )
        headline = (
            f"{_display_verdict(verdict)}: {point:.0f}/100 model score "
            f"({score_low:.0f}-{score_high:.0f})"
        )
        quality.freshness["stats_health"] = stats_health

        return TradeAnalysis(
            headline=headline,
            verdict=verdict,
            model_score_low=score_low,
            model_score_high=score_high,
            model_score_point=point,
            score_interpretation=(
                "This is a normalized decision score out of 100, not an empirical win probability. "
                "A win-rate claim is withheld until labeled trade outcomes meet the calibration evidence floor."
            ),
            assets=assets,
            lineup_impacts=lineup_impacts,
            scenarios=scenarios,
            negotiation=TradeNegotiationLadder(
                **offers,
                walk_away_rule=(
                    f"Walk away below {_HOLD_THRESHOLD:.0f}/100, if a required asset loses verified identity, "
                    "or if the lineup thesis is no longer supported by fresh evidence."
                ),
            ),
            quality=quality,
            key_reasons=list(dict.fromkeys(key_reasons)),
            contrary_case=contrary_case,
            what_changes_the_answer=what_changes,
        )

    def _load_context(self, request: TradeRequest) -> None:
        try:
            roster_rows = self._conn.execute(
                """
                SELECT roster_id, owner_id, owner_display_name, players
                FROM rosters
                WHERE league_id = ?
                ORDER BY roster_id
                """,
                [request.league_id],
            ).fetchall()
        except duckdb.Error:
            roster_rows = []

        for row in roster_rows:
            roster_id = int(row[0])
            self._roster_names[roster_id] = str(
                row[2] or row[1] or f"Roster {roster_id}"
            )
            try:
                players = json.loads(row[3] or "[]")
            except (TypeError, json.JSONDecodeError):
                players = []
            for player_id in players if isinstance(players, list) else []:
                normalized_id = str(player_id)
                self._player_owners.setdefault(normalized_id, roster_id)

        player_ids = sorted(
            {
                str(asset.player_id)
                for asset in self._all_core_assets(request)
                if asset.asset_type == "player" and asset.player_id is not None
            }
        )
        if player_ids:
            try:
                rows = self._conn.execute(
                    """
                    SELECT player_id, full_name, position, age
                    FROM players
                    WHERE player_id IN (SELECT UNNEST(?))
                    """,
                    [player_ids],
                ).fetchall()
            except duckdb.Error:
                rows = []
            self._player_catalog = {
                str(row[0]): {
                    "full_name": str(row[1] or row[0]),
                    "position": str(row[2] or "UNKNOWN"),
                    "age": int(row[3]) if row[3] is not None else None,
                }
                for row in rows
            }
            try:
                rows = self._repo.get_player_values(
                    player_ids,
                    request.league_id,
                    request.user_roster_id,
                )
            except duckdb.Error:
                rows = []
            self._player_values = {
                str(row["player_id"]): row for row in rows if row.get("player_id")
            }

        try:
            self._pick_inventory = self._repo.get_picks_for_league(request.league_id)
        except duckdb.Error:
            self._pick_inventory = []

    def _all_core_assets(self, request: TradeRequest) -> list[TradeAsset]:
        assets = list(request.user_sends) + list(request.user_receives)
        for leg in request.third_party_trades or []:
            assets.extend(leg.sends)
            assets.extend(leg.receives)
        return assets

    def _build_assets(self, request: TradeRequest) -> list[TradeAnalysisAsset]:
        result: list[TradeAnalysisAsset] = []
        for side, assets in (
            ("user_send", request.user_sends),
            ("user_receive", request.user_receives),
        ):
            result.extend(self._asset_evidence(request, side, assets))
        if request.counterparty_roster_id is not None:
            result.extend(
                self._asset_evidence(
                    request,
                    "counterparty_send",
                    request.user_receives,
                )
            )
            result.extend(
                self._asset_evidence(
                    request,
                    "counterparty_receive",
                    request.user_sends,
                )
            )
        return result

    def _asset_evidence(
        self,
        request: TradeRequest,
        side: str,
        assets: list[TradeAsset],
    ) -> list[TradeAnalysisAsset]:
        result: list[TradeAnalysisAsset] = []
        for asset in assets:
            key = _asset_key(asset)
            cached = self._asset_cache.get(key)
            if cached is None:
                cached = self._resolve_asset_evidence(request, asset)
                self._asset_cache[key] = cached
            result.append(cached.model_copy(update={"side": side}))
        return result

    def _resolve_asset_evidence(
        self,
        request: TradeRequest,
        asset: TradeAsset,
    ) -> TradeAnalysisAsset:
        notes: list[str] = []
        current_owner_id: int | None = None
        current_owner_name: str | None = None
        original_owner_name: str | None = None
        position: str | None = None
        age: int | None = None
        market_value: float | None = None
        context_value: float | None = None
        valuation_source = "unavailable"
        evidence_status: str = "unavailable"
        label = asset.label or "Unknown asset"
        normalized_asset = asset.model_copy(deep=True)

        if asset.asset_type == "player" and asset.player_id is not None:
            player_id = str(asset.player_id)
            catalog = self._player_catalog.get(player_id)
            value = self._player_values.get(player_id)
            if catalog is not None:
                label = str(catalog["full_name"])
                position = str(catalog["position"])
                raw_age = catalog.get("age")
                age = int(raw_age) if isinstance(raw_age, int) else None
            else:
                label = player_id
                notes.append("Player identity is not present in the local player catalog.")
            current_owner_id = self._player_owners.get(player_id)
            if current_owner_id is not None:
                current_owner_name = self._roster_names.get(
                    current_owner_id,
                    f"Roster {current_owner_id}",
                )
            else:
                notes.append("Current player ownership is not present in the local roster snapshot.")
            if value is None:
                notes.append("No local player-value row is available for this asset.")
            else:
                market_value = _optional_float(value.get("lens_market"))
                context_value = _asset_context_value(value)
                valuation_source = "player_values"
                if market_value is None:
                    notes.append("The player-value row is missing its market lens.")
                else:
                    evidence_status = "available"
            normalized_asset.label = label
        elif asset.asset_type == "pick":
            pick = self._find_pick(asset)
            if pick is None:
                notes.append(
                    "The pick does not match a locally ingested original-owner, year, and round identity."
                )
            else:
                current_owner_id = int(pick["current_owner_id"])
                current_owner_name = str(pick["current_owner_name"])
                original_owner_name = str(pick["original_owner_name"])
                if not asset.projected_slot and pick.get("projected_slot"):
                    normalized_asset.projected_slot = str(pick["projected_slot"])
                label = (
                    f"{asset.pick_year} Round {asset.pick_round}"
                    + (
                        f" ({normalized_asset.projected_slot})"
                        if normalized_asset.projected_slot
                        else ""
                    )
                )
            try:
                pick_value = self._repo.get_pick_value(
                    asset,
                    request.league_id,
                    target_roster_id=request.user_roster_id,
                )
            except Exception as exc:
                pick_value = None
                notes.append(f"Pick valuation is unavailable: {exc}")
            if pick_value is not None:
                market_value = _safe_float(pick_value.demand_adjusted_value) / 100.0
                context_value = _safe_float(pick_value.league_adjusted_value) / 100.0
                valuation_source = "pick_engine"
                notes.extend(str(reason) for reason in pick_value.degradation_reasons)
                if pick_value.rule_citation is None:
                    notes.append("No league draft-order rule citation is available for this pick.")
                if not notes:
                    evidence_status = "available"
                else:
                    evidence_status = "degraded"
            normalized_asset.label = label
        else:
            notes.append("Unsupported asset type.")

        if evidence_status == "unavailable" and market_value is not None:
            evidence_status = "degraded"
        if not notes and evidence_status == "unavailable":
            notes.append("No valuation evidence is available for this asset.")

        return TradeAnalysisAsset(
            side="user_send",
            asset=normalized_asset,
            label=label,
            position=position,
            age=age,
            current_owner_roster_id=current_owner_id,
            current_owner_name=current_owner_name,
            original_owner_name=original_owner_name,
            market_value=market_value,
            context_value=context_value,
            valuation_source=valuation_source,
            evidence_status=evidence_status,
            evidence_notes=list(dict.fromkeys(notes)),
        )

    def _find_pick(self, asset: TradeAsset) -> dict[str, Any] | None:
        if (
            asset.pick_owner_roster_id is None
            or asset.pick_year is None
            or asset.pick_round is None
        ):
            return None
        return next(
            (
                pick
                for pick in self._pick_inventory
                if int(pick["original_owner_id"]) == int(asset.pick_owner_roster_id)
                and int(pick["pick_year"]) == int(asset.pick_year)
                and int(pick["round"]) == int(asset.pick_round)
            ),
            None,
        )

    def _freshness(
        self,
        league_id: str,
    ) -> tuple[dict[str, object], int | None]:
        league_season: int | None = None
        completed_at: str | None = None
        source = "unknown"
        try:
            row = self._conn.execute(
                "SELECT season, CAST(ingested_at AS VARCHAR) FROM leagues WHERE league_id = ?",
                [league_id],
            ).fetchone()
            if row is not None:
                league_season = int(row[0])
                completed_at = str(row[1]) if row[1] is not None else None
                source = "leagues.ingested_at"
        except (duckdb.Error, TypeError, ValueError):
            pass
        try:
            row = self._conn.execute(
                """
                SELECT CAST(completed_at AS VARCHAR)
                FROM ingest_runs
                WHERE league_id = ? AND completed_at IS NOT NULL
                ORDER BY completed_at DESC, id DESC
                LIMIT 1
                """,
                [league_id],
            ).fetchone()
            if row is not None and row[0] is not None:
                completed_at = str(row[0])
                source = "ingest_runs.completed_at"
        except duckdb.Error:
            pass

        parsed = _parse_timestamp(completed_at)
        age_hours = (
            max((datetime.now(timezone.utc) - parsed).total_seconds() / 3600.0, 0.0)
            if parsed is not None
            else None
        )
        status = (
            "unknown"
            if age_hours is None
            else "stale"
            if age_hours > _STALE_AFTER_HOURS
            else "fresh"
        )
        freshness: dict[str, object] = {
            "status": status,
            "source": source,
            "completed_at": completed_at,
            "age_hours": round(age_hours, 2) if age_hours is not None else None,
            "stale_after_hours": _STALE_AFTER_HOURS,
        }
        return freshness, league_season

    def _stats_health(self, league_season: int | None) -> dict[str, object]:
        if league_season is None:
            return {
                "status": "missing",
                "integrity_status": "unknown",
                "scoring_status": "unavailable",
                "issues": [{"message": "League season is unavailable."}],
            }
        try:
            return assess_stats_health(self._conn, league_season).model_dump()
        except duckdb.Error as exc:
            return {
                "status": "missing",
                "integrity_status": "unknown",
                "scoring_status": "unavailable",
                "issues": [{"message": f"Stats health check failed: {exc}"}],
            }

    def _calibration(self) -> dict[str, object]:
        try:
            return calibration_evidence(self._conn)
        except duckdb.Error as exc:
            return {
                "status": "unavailable",
                "sample_size": 0,
                "message": f"Calibration evidence check failed: {exc}",
            }

    def _build_lineup_impacts(
        self,
        request: TradeRequest,
        stats_health: dict[str, object],
        freshness: dict[str, object],
    ) -> tuple[list[TradeLineupImpact], bool]:
        participants = self._participant_transfers(request)
        if not participants:
            return [], False

        try:
            roster_ids = [
                int(row[0])
                for row in self._conn.execute(
                    "SELECT roster_id FROM rosters WHERE league_id = ? ORDER BY roster_id",
                    [request.league_id],
                ).fetchall()
            ]
            scorecard_engine = ScorecardEngine(self._conn)
            inputs_map: dict[int, ScorecardInputs] = {
                roster_id: scorecard_engine._apply_corrections(
                    scorecard_engine._gather_inputs(request.league_id, roster_id),
                    request.league_id,
                    roster_id,
                )
                for roster_id in roster_ids
            }
            self._augment_trade_players(inputs_map, request)
            scorecards = scorecard_engine.compute_all(request.league_id)
            lineup_engine = LineupEngine(self._conn)
            before = lineup_engine.compute_all(request.league_id, inputs_map, scorecards)
            after_inputs = {
                roster_id: inputs.model_copy(deep=True)
                for roster_id, inputs in inputs_map.items()
            }
            for roster_id, (sends, receives) in participants.items():
                if roster_id not in after_inputs:
                    continue
                self._apply_transfer(after_inputs[roster_id], sends, receives)
            after = lineup_engine.compute_all(
                request.league_id,
                after_inputs,
                scorecards,
            )
        except Exception as exc:
            return [
                TradeLineupImpact(
                    roster_id=roster_id,
                    roster_name=self._roster_names.get(roster_id, f"Roster {roster_id}"),
                    status="unavailable",
                    notes=[f"Before/after lineup simulation is unavailable: {exc}"],
                )
                for roster_id in participants
            ], False

        health_status = str(stats_health.get("status") or "missing")
        freshness_status = str(freshness.get("status") or "unknown")
        degraded = health_status != "valid" or freshness_status != "fresh"
        impacts: list[TradeLineupImpact] = []
        for roster_id in participants:
            before_result = before.get(roster_id)
            after_result = after.get(roster_id)
            if before_result is None or after_result is None:
                impacts.append(
                    TradeLineupImpact(
                        roster_id=roster_id,
                        roster_name=self._roster_names.get(roster_id, f"Roster {roster_id}"),
                        status="unavailable",
                        notes=["Roster lineup result was not produced."],
                    )
                )
                continue
            notes = [
                "Before and after lineups are optimized from the same local roster inputs."
            ]
            if health_status != "valid":
                notes.append(f"Stats health is {health_status}; lineup result is not fully trusted.")
            if freshness_status != "fresh":
                notes.append("League ingest is not fresh at analysis time.")
            impacts.append(
                TradeLineupImpact(
                    roster_id=roster_id,
                    roster_name=self._roster_names.get(roster_id, f"Roster {roster_id}"),
                    status="degraded" if degraded else "available",
                    before_title_window=str(before_result.title_window_label),
                    after_title_window=str(after_result.title_window_label),
                    before_score=round(float(before_result.total_lineup_score), 4),
                    after_score=round(float(after_result.total_lineup_score), 4),
                    score_delta=round(
                        float(after_result.total_lineup_score)
                        - float(before_result.total_lineup_score),
                        4,
                    ),
                    starter_changes=self._starter_changes(before_result, after_result),
                    notes=notes,
                )
            )
        return impacts, any(impact.status != "unavailable" for impact in impacts)

    def _participant_transfers(
        self,
        request: TradeRequest,
    ) -> dict[int, tuple[list[str], list[str]]]:
        transfers: dict[int, tuple[list[str], list[str]]] = {}

        def player_ids(assets: list[TradeAsset]) -> list[str]:
            return [
                str(asset.player_id)
                for asset in assets
                if asset.asset_type == "player" and asset.player_id is not None
            ]

        transfers[request.user_roster_id] = (
            player_ids(request.user_sends),
            player_ids(request.user_receives),
        )
        if request.counterparty_roster_id is not None:
            transfers[request.counterparty_roster_id] = (
                player_ids(request.user_receives),
                player_ids(request.user_sends),
            )
        for leg in request.third_party_trades or []:
            previous_sends, previous_receives = transfers.get(leg.roster_id, ([], []))
            transfers[leg.roster_id] = (
                previous_sends + player_ids(leg.sends),
                previous_receives + player_ids(leg.receives),
            )
        return transfers

    def _augment_trade_players(
        self,
        inputs_map: dict[int, ScorecardInputs],
        request: TradeRequest,
    ) -> None:
        player_ids = sorted(
            {
                player_id
                for sends, receives in self._participant_transfers(request).values()
                for player_id in sends + receives
            }
        )
        if not player_ids:
            return

        stats_seasons = {
            inputs.stats_season
            for inputs in inputs_map.values()
            if inputs.stats_season is not None
        }
        stats_by_player: dict[str, tuple[float, int]] = {}
        if stats_seasons:
            stats_season = max(stats_seasons)
            try:
                rows = self._conn.execute(
                    """
                    SELECT player_id, AVG(fantasy_points), COUNT(*)
                    FROM player_stats_weekly
                    WHERE player_id IN (SELECT UNNEST(?)) AND season = ?
                    GROUP BY player_id
                    """,
                    [player_ids, stats_season],
                ).fetchall()
                stats_by_player = {
                    str(row[0]): (_safe_float(row[1]), int(row[2] or 0))
                    for row in rows
                }
            except duckdb.Error:
                pass

        adp_by_player: dict[str, float] = {}
        try:
            rows = self._conn.execute(
                """
                SELECT player_id, adp
                FROM player_adp_baseline
                WHERE player_id IN (SELECT UNNEST(?))
                """,
                [player_ids],
            ).fetchall()
            adp_by_player = {
                str(row[0]): _safe_float(row[1]) for row in rows if row[1] is not None
            }
        except duckdb.Error:
            pass

        for inputs in inputs_map.values():
            for player_id in player_ids:
                catalog = self._player_catalog.get(player_id, {})
                inputs.player_positions.setdefault(
                    player_id,
                    str(catalog.get("position") or "UNKNOWN"),
                )
                raw_age = catalog.get("age")
                if isinstance(raw_age, int):
                    inputs.player_ages.setdefault(player_id, raw_age)
                if player_id in stats_by_player:
                    average, games = stats_by_player[player_id]
                    inputs.weekly_fantasy_pts.setdefault(player_id, average)
                    inputs.player_games_played.setdefault(player_id, games)
                if player_id in adp_by_player:
                    inputs.adp_ranks.setdefault(player_id, adp_by_player[player_id])

    def _apply_transfer(
        self,
        inputs: ScorecardInputs,
        sends: list[str],
        receives: list[str],
    ) -> None:
        send_ids = set(sends)
        receive_ids = set(receives)
        for field in ("starters", "bench", "ir", "taxi"):
            current = getattr(inputs, field)
            setattr(inputs, field, [player_id for player_id in current if player_id not in send_ids])
        present = set(inputs.starters + inputs.bench + inputs.ir + inputs.taxi)
        inputs.bench.extend(
            player_id
            for player_id in receives
            if player_id not in present and player_id not in send_ids
        )

    def _starter_changes(
        self,
        before: LineupResult,
        after: LineupResult,
    ) -> list[str]:
        changes: list[str] = []
        width = max(len(before.slot_scores), len(after.slot_scores))
        for index in range(width):
            before_slot = before.slot_scores[index] if index < len(before.slot_scores) else None
            after_slot = after.slot_scores[index] if index < len(after.slot_scores) else None
            before_id = before_slot.player_id if before_slot else None
            after_id = after_slot.player_id if after_slot else None
            if before_id == after_id:
                continue
            position = (after_slot or before_slot).position
            before_name = before_slot.player_name if before_slot else "empty"
            after_name = after_slot.player_name if after_slot else "empty"
            changes.append(f"{position}: {before_name} -> {after_name}")
        return changes or ["No projected starter changes."]

    def _score_evaluation(self, evaluation: TradeEvaluation) -> float:
        weighted_score = 0.0
        total_weight = 0.0
        for name, weight in DIMENSION_WEIGHTS.items():
            dimension = getattr(evaluation, name)
            weighted_score += float(dimension.score) * float(weight)
            total_weight += float(weight)
        return _clamp_score(weighted_score / max(total_weight, 0.01))

    def _score_band(
        self,
        point: float,
        assets: list[TradeAnalysisAsset],
        lineup_impacts: list[TradeLineupImpact],
        freshness: dict[str, object],
        stats_health: dict[str, object],
        calibration: dict[str, object],
        evaluation: TradeEvaluation,
    ) -> tuple[float, float]:
        uncertainty = 4.0
        low_confidence_count = sum(
            1
            for name in _DIMENSION_NAMES
            if getattr(evaluation, name).confidence == "LOW"
        )
        uncertainty += min(6.0, low_confidence_count * 2.0)
        if freshness.get("status") != "fresh":
            uncertainty += 8.0
        if stats_health.get("status") != "valid":
            uncertainty += 6.0
        if calibration.get("status") != "available":
            uncertainty += 4.0
        if any(asset.evidence_status == "degraded" for asset in assets):
            uncertainty += 3.0
        if any(asset.evidence_status == "unavailable" for asset in assets):
            uncertainty += 6.0
        if any(impact.status == "unavailable" for impact in lineup_impacts):
            uncertainty += 5.0
        if evaluation.degradation_reasons:
            uncertainty += 2.0
        uncertainty = min(25.0, uncertainty)
        return (
            _clamp_score(point - uncertainty),
            _clamp_score(point + uncertainty),
        )

    def _build_scenarios(
        self,
        request: TradeRequest,
        evaluation: TradeEvaluation,
        assets: list[TradeAnalysisAsset],
        lineup_impacts: list[TradeLineupImpact],
        stats_health: dict[str, object],
        freshness: dict[str, object],
        calibration: dict[str, object],
    ) -> tuple[list[TradeAnalysisScenario], dict[str, TradeAnalysisOffer]]:
        package = self._build_package_fallback(request, evaluation)
        offers = {
            "aggressive_open": self._offer_from_package(
                package.aggressive_open,
                "aggressive_open",
                "Start with the strongest ask that still preserves a coherent lineup path.",
            ),
            "preferred_close": self._offer_from_package(
                package.fair_close,
                "preferred_close",
                "Use this as the fair closing structure for the current trade thesis.",
            ),
            "fallback": self._offer_from_package(
                package.roster_fit_counter or package.fair_close,
                "fallback",
                "Use this only if the counterparty rejects the preferred close and the lineup gain remains real.",
            ),
        }
        offers["walk_away"] = TradeAnalysisOffer(
            label="Walk-Away Floor",
            send_assets=list(offers["fallback"].send_assets),
            receive_assets=list(offers["fallback"].receive_assets),
            purpose="walk_away",
            rationale=(
                "Do not add value beyond the fallback package without a new, verified reason "
                "that improves your lineup or strategic position."
            ),
        )

        current_point = self._score_evaluation(evaluation)
        scenarios: list[TradeAnalysisScenario] = []
        current_low, current_high = self._score_band(
            current_point,
            assets,
            lineup_impacts,
            freshness,
            stats_health,
            calibration,
            evaluation,
        )
        scenarios.append(
            TradeAnalysisScenario(
                label="Current Offer",
                scenario_type="current_offer",
                score_low=current_low,
                score_high=current_high,
                score_point=current_point,
                verdict=_score_verdict(current_point),
                rationale="Scores the exact send and receive lists submitted to Trade Lab.",
                assumptions=self._scenario_assumptions(request, assets),
            )
        )

        scenario_types = (
            ("aggressive_open", "Aggressive Open"),
            ("preferred_close", "Preferred Close"),
            ("fallback", "Roster-Fit Fallback"),
        )
        for key, label in scenario_types:
            offer = offers[key]
            variant_score = self._evaluate_offer(request, offer)
            if variant_score is None:
                scenarios.append(
                    TradeAnalysisScenario(
                        label=label,
                        scenario_type=key,
                        verdict="hold",
                        rationale="Variant scoring is unavailable; do not treat this package as validated.",
                        assumptions=["The underlying package could not be independently re-scored."],
                    )
                )
                continue
            low, high = self._score_band(
                variant_score,
                assets,
                lineup_impacts,
                freshness,
                stats_health,
                calibration,
                evaluation,
            )
            scenarios.append(
                TradeAnalysisScenario(
                    label=label,
                    scenario_type=key,
                    score_low=low,
                    score_high=high,
                    score_point=variant_score,
                    verdict=_score_verdict(variant_score),
                    rationale=offer.rationale,
                    assumptions=self._scenario_assumptions(request, assets),
                )
            )
        scenarios.append(
            TradeAnalysisScenario(
                label="Walk Away",
                scenario_type="walk_away",
                verdict="walk_away",
                rationale="Hold the assets rather than accept a package below the fallback floor.",
                assumptions=[
                    f"Walk away below {_HOLD_THRESHOLD:.0f}/100 unless new evidence changes the thesis.",
                    "A score below the evidence floor is not converted into a win probability.",
                ],
            )
        )
        return scenarios, offers

    def _build_package_fallback(
        self,
        request: TradeRequest,
        evaluation: TradeEvaluation,
    ) -> PackageBuilderResult:
        if evaluation.package is not None:
            return evaluation.package
        generic = PackageOffer(
            label="Current Offer",
            send_assets=list(request.user_sends),
            receive_assets=list(request.user_receives),
            reasoning="No package-builder output was requested; this is the submitted offer only.",
        )
        return PackageBuilderResult(
            aggressive_open=generic,
            fair_close=generic.model_copy(update={"label": "Preferred Close"}),
            roster_fit_counter=None,
        )

    def _offer_from_package(
        self,
        package: PackageOffer,
        purpose: _OFFER_PURPOSE,
        rationale: str,
    ) -> TradeAnalysisOffer:
        return TradeAnalysisOffer(
            label=package.label,
            send_assets=list(package.send_assets),
            receive_assets=list(package.receive_assets),
            purpose=purpose,
            rationale=f"{rationale} {package.reasoning}",
        )

    def _evaluate_offer(
        self,
        request: TradeRequest,
        offer: TradeAnalysisOffer,
    ) -> float | None:
        from fantasy.trade.trade_engine import TradeEngine

        variant = request.model_copy(deep=True)
        variant.user_sends = [asset.model_copy(deep=True) for asset in offer.send_assets]
        variant.user_receives = [
            asset.model_copy(deep=True) for asset in offer.receive_assets
        ]
        variant.include_package = False
        variant.include_reroutes = False
        try:
            evaluation = TradeEngine(self._conn).evaluate(
                variant,
                include_recommendation_cards=False,
                include_analysis=False,
            )
        except Exception:
            return None
        return self._score_evaluation(evaluation)

    def _scenario_assumptions(
        self,
        request: TradeRequest,
        assets: list[TradeAnalysisAsset],
    ) -> list[str]:
        assumptions = [
            "The league format and current roster snapshot are the local source of truth.",
            "Pick value depends on the verified original owner, projected range, and league draft-order rules.",
        ]
        if any(asset.evidence_status != "available" for asset in assets):
            assumptions.append("At least one asset has degraded or unavailable valuation evidence.")
        if request.third_party_trades:
            assumptions.append(
                "Third-party market legs are scored; their full lineup effects are shown only for locally represented rosters."
            )
        return assumptions

    def _build_gates(
        self,
        request: TradeRequest,
        assets: list[TradeAnalysisAsset],
        evaluation: TradeEvaluation,
        lineup_available: bool,
        scenarios: list[TradeAnalysisScenario],
        offers: dict[str, TradeAnalysisOffer],
        calibration: dict[str, object],
    ) -> dict[str, bool]:
        all_requested_assets = self._all_core_assets(request)
        exact_offer = bool(request.user_sends and request.user_receives) and all(
            (
                asset.asset_type == "player"
                and asset.player_id is not None
            )
            or (
                asset.asset_type == "pick"
                and asset.pick_owner_roster_id is not None
                and asset.pick_year is not None
                and asset.pick_round is not None
            )
            for asset in all_requested_assets
        )
        pick_assets = [asset for asset in assets if asset.asset.asset_type == "pick"]
        pick_identity = all(
            asset.current_owner_roster_id is not None for asset in pick_assets
        )
        asset_valuations = bool(assets) and all(
            asset.evidence_status != "unavailable" for asset in assets
        )
        participant_ids = set(self._roster_names)
        counterparty_context = (
            request.counterparty_roster_id is not None
            and request.counterparty_roster_id in participant_ids
        )
        scored_scenarios = sum(
            scenario.score_point is not None
            for scenario in scenarios
            if scenario.scenario_type != "walk_away"
        )
        package_scenarios = evaluation.package is not None and scored_scenarios >= 4
        return {
            "exact_offer": exact_offer,
            "format_context": bool(self._roster_names) and bool(self._player_catalog or assets),
            "asset_valuations": asset_valuations,
            "pick_identity": pick_identity,
            "lineup_before_after": lineup_available,
            "counterparty_context": counterparty_context,
            "scenario_analysis": package_scenarios,
            "negotiation_ladder": all(
                bool(offers[key].send_assets or offers[key].receive_assets)
                for key in ("aggressive_open", "preferred_close", "fallback", "walk_away")
            ),
            "calibration_truth": calibration.get("status") == "available",
        }

    def _build_quality(
        self,
        gates: dict[str, bool],
        assets: list[TradeAnalysisAsset],
        lineup_impacts: list[TradeLineupImpact],
        freshness: dict[str, object],
        stats_health: dict[str, object],
        calibration: dict[str, object],
        evaluation: TradeEvaluation,
    ) -> TradeAnalysisQuality:
        structural_names = (
            "exact_offer",
            "format_context",
            "asset_valuations",
            "pick_identity",
            "lineup_before_after",
            "counterparty_context",
            "scenario_analysis",
            "negotiation_ladder",
        )
        completeness = round(
            100.0
            * sum(gates.get(name, False) for name in structural_names)
            / len(structural_names),
            2,
        )
        reliability = 100.0
        freshness_status = str(freshness.get("status") or "unknown")
        stats_status = str(stats_health.get("status") or "missing")
        calibration_status = str(calibration.get("status") or "unavailable")
        if freshness_status == "stale":
            reliability -= 25.0
        elif freshness_status == "unknown":
            reliability -= 15.0
        if stats_status == "degraded":
            reliability -= 15.0
        elif stats_status in {"blocked", "missing"}:
            reliability -= 30.0
        if calibration_status != "available":
            reliability -= 15.0
        reliability -= sum(
            10.0 if asset.evidence_status == "unavailable" else 4.0
            for asset in assets
        )
        if any(impact.status == "unavailable" for impact in lineup_impacts):
            reliability -= 10.0
        if evaluation.degradation_reasons:
            reliability -= 4.0
        reliability = round(max(0.0, min(100.0, reliability)), 2)
        critical_missing = not all(
            gates.get(name, False)
            for name in ("exact_offer", "format_context", "asset_valuations")
        )
        if critical_missing:
            status = "blocked"
        elif (
            completeness == 100.0
            and reliability >= 85.0
            and freshness_status == "fresh"
            and stats_status == "valid"
            and calibration_status == "available"
        ):
            status = "complete"
        else:
            status = "complete_with_degraded_evidence"

        limitations: list[str] = []
        if freshness_status != "fresh":
            limitations.append(
                "League ingest is not fresh enough for an unqualified current-market claim."
            )
        if stats_status != "valid":
            limitations.append(
                f"Stats inputs are {stats_status}; lineup and production context are marked degraded."
            )
        if calibration_status != "available":
            limitations.append(
                "No calibration run with the required labeled-outcome sample is available; the score is not a win probability."
            )
        if not gates.get("pick_identity", True):
            limitations.append(
                "At least one pick is missing a verified local ownership and projected-slot match."
            )
        if not gates.get("counterparty_context", False):
            limitations.append(
                "Counterparty identity is missing or not present in the local league snapshot."
            )
        limitations.extend(evaluation.degradation_reasons)
        return TradeAnalysisQuality(
            completeness_score=completeness,
            evidence_reliability_score=reliability,
            status=status,
            gates=gates,
            limitations=list(dict.fromkeys(limitations)),
            freshness=dict(freshness),
            calibration=dict(calibration),
        )

    def _key_reasons(self, evaluation: TradeEvaluation) -> list[str]:
        ranked: list[tuple[float, str]] = []
        for name in _DIMENSION_NAMES:
            dimension: DimensionScore = getattr(evaluation, name)
            ranked.append((abs(float(dimension.score) - 50.0), dimension.reasoning))
        ranked.sort(reverse=True, key=lambda item: item[0])
        return [reason for _, reason in ranked[:3]]

    def _contrary_case(self, evaluation: TradeEvaluation) -> str:
        weakest_name = min(
            _DIMENSION_NAMES,
            key=lambda name: float(getattr(evaluation, name).score),
        )
        weakest: DimensionScore = getattr(evaluation, weakest_name)
        return (
            f"The strongest contrary case is {weakest_name.replace('_', ' ')} at "
            f"{weakest.score:.0f}/100: {weakest.reasoning}"
        )

    def _what_changes_the_answer(
        self,
        request: TradeRequest,
        assets: list[TradeAnalysisAsset],
        freshness: dict[str, object],
        stats_health: dict[str, object],
        calibration: dict[str, object],
    ) -> list[str]:
        changes: list[str] = []
        if freshness.get("status") != "fresh":
            changes.append("A fresh league ingest could narrow the current-market uncertainty band.")
        if stats_health.get("status") != "valid":
            changes.append("A valid, non-cloned stats season could change production and lineup deltas.")
        if any(asset.asset.asset_type == "pick" for asset in assets):
            changes.append("A verified pick owner, draft-order rule, and projected range could change the pick premium.")
        if calibration.get("status") != "available":
            changes.append("At least 20 labeled trade outcomes are required before reporting an empirical win rate.")
        if request.third_party_trades:
            changes.append("A verified third-party lineup simulation could change the multi-team recommendation.")
        return list(dict.fromkeys(changes))

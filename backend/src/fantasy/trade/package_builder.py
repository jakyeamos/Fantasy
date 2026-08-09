from __future__ import annotations

import duckdb

from fantasy.intelligence.positional_context import PositionalContext
from fantasy.rookie_pick.constants import (
    MIN_ROOKIE_PICK_EVIDENCE,
    PICK_PREMIUM_THRESHOLD,
)
from fantasy.rookie_pick.rookie_pick_repo import RookiePickRepo
from fantasy.trade.models import (
    DimensionScore,
    PackageBuilderResult,
    PackageOffer,
    ParticipantPackageOffer,
    TradeEvaluation,
    TradeAsset,
    TradeRequest,
)
from fantasy.trade.trade_repo import TradeRepo


class PackageBuilder:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._repo = TradeRepo(conn)

    def _label_assets(self, league_id: str, assets: list[TradeAsset]) -> list[TradeAsset]:
        player_ids = [
            str(asset.player_id)
            for asset in assets
            if asset.asset_type == "player" and asset.player_id is not None
        ]
        names = {
            str(row[0]): str(row[1] or row[0])
            for row in self._conn.execute(
                """
                SELECT player_id, full_name
                FROM players
                WHERE player_id IN (SELECT UNNEST(?))
                """,
                [player_ids],
            ).fetchall()
        } if player_ids else {}
        labeled: list[TradeAsset] = []
        for asset in assets:
            copy = asset.model_copy(deep=True)
            if copy.asset_type == "player" and copy.player_id is not None:
                copy.label = names.get(str(copy.player_id), str(copy.player_id))
            elif copy.asset_type == "pick":
                slot = f" ({copy.projected_slot})" if copy.projected_slot else ""
                copy.label = f"{copy.pick_year} Round {copy.pick_round}{slot}"
            labeled.append(copy)
        return labeled

    def _lineup_upgrade_candidates(
        self, request: TradeRequest
    ) -> list[dict[str, object]]:
        if request.counterparty_roster_id is None:
            return []
        roster_players = self._repo.get_roster_players(
            request.league_id, request.counterparty_roster_id
        )
        excluded_ids = {
            str(asset.player_id)
            for asset in request.user_receives
            if asset.asset_type == "player" and asset.player_id is not None
        }
        incoming_positions = {
            str(row[0])
            for row in self._conn.execute(
                """
                SELECT COALESCE(position, 'UNKNOWN')
                FROM players
                WHERE player_id IN (SELECT UNNEST(?))
                """,
                [list(excluded_ids)],
            ).fetchall()
        } if excluded_ids else set()
        values = self._repo.get_player_values(
            [player["player_id"] for player in roster_players],
            request.league_id,
            request.user_roster_id,
        )
        context = PositionalContext(
            self._conn, request.league_id, request.user_roster_id
        )
        ranked: list[dict[str, object]] = []
        for value in values:
            player_id = str(value["player_id"])
            position = str(value.get("position") or "UNKNOWN")
            if player_id in excluded_ids or position not in {"QB", "RB", "WR", "TE"}:
                continue
            if position == "QB" and context.surplus_units(position) > 0:
                continue
            if position in incoming_positions and context.surplus_units(position) > 0:
                continue
            fit, notes = context.trade_receive_value(value)
            production = float(value.get("lens_production") or 0.0)
            market = float(value.get("lens_market") or 0.0)
            surplus_penalty = 0.12 if any("surplus" in note for note in notes) else 0.0
            score = fit * 0.45 + production * 0.35 + market * 0.20 - surplus_penalty
            ranked.append(
                {
                    "player_id": player_id,
                    "full_name": str(value.get("full_name") or player_id),
                    "position": position,
                    "score": score,
                    "notes": notes,
                }
            )
        ranked.sort(key=lambda item: float(item["score"]), reverse=True)
        return ranked

    def build(
        self,
        request: TradeRequest,
        evaluation: TradeEvaluation,
    ) -> PackageBuilderResult | None:
        manager_profile = (
            self._repo.get_manager_profile(request.league_id, request.counterparty_roster_id)
            if request.counterparty_roster_id is not None
            else None
        )
        pitch_angles = (
            self._repo.get_pitch_angles(request.league_id, request.counterparty_roster_id)
            if request.counterparty_roster_id is not None
            else []
        )
        labeled_sends = self._label_assets(request.league_id, list(request.user_sends))
        labeled_receives = self._label_assets(request.league_id, list(request.user_receives))
        fair_close = PackageOffer(
            label="Fair Close",
            send_assets=labeled_sends,
            receive_assets=labeled_receives,
            reasoning=(
                "Balances current market value with your roster direction without leaning too hard on the counterparty profile."
                if not request.third_party_trades
                else "Balances your net swap while the scored sidecar legs establish whether the extra team can accept the structure."
            ),
        )

        aggressive_sends = list(labeled_sends)
        if manager_profile and manager_profile.get("exploitation_primary") == "value_loss" and len(aggressive_sends) > 1:
            aggressive_sends = aggressive_sends[:-1]
        aggressive_reasoning = (
            pitch_angles[0]["reasoning"]
            if pitch_angles
            else "Leans into the counterparty's documented weaknesses while staying structurally coherent."
        )
        if request.third_party_trades:
            aggressive_reasoning = (
                aggressive_reasoning
                + " Multi-team sidecar legs now feed participant-specific package framing."
            )
        upgrade_candidates = self._lineup_upgrade_candidates(request)
        core_receives = [
            asset for asset in labeled_receives if asset.asset_type == "player"
        ]
        if upgrade_candidates:
            top_target = upgrade_candidates[0]
            aggressive_receives = core_receives + [
                TradeAsset(
                    asset_type="player",
                    player_id=str(top_target["player_id"]),
                    label=str(top_target["full_name"]),
                )
            ]
            aggressive_reasoning = (
                f"Open by replacing distant or redundant value with {top_target['full_name']}, "
                f"the strongest lineup-fit target on this manager's roster at {top_target['position']}. "
                + aggressive_reasoning
            )
        else:
            aggressive_receives = list(labeled_receives)
        aggressive_open = PackageOffer(
            label="Aggressive Open",
            send_assets=aggressive_sends,
            receive_assets=aggressive_receives,
            reasoning=aggressive_reasoning,
        )
        roster_fit_counter: PackageOffer | None = None
        if len(upgrade_candidates) >= 2:
            second_target = upgrade_candidates[1]
            nearest_first = next(
                (
                    asset
                    for asset in sorted(
                        labeled_receives,
                        key=lambda item: item.pick_year or 9999,
                    )
                    if asset.asset_type == "pick" and asset.pick_round == 1
                ),
                None,
            )
            counter_receives = core_receives + [
                TradeAsset(
                    asset_type="player",
                    player_id=str(second_target["player_id"]),
                    label=str(second_target["full_name"]),
                )
            ]
            if nearest_first is not None:
                counter_receives.append(nearest_first)
            roster_fit_counter = PackageOffer(
                label="Roster-Fit Counter",
                send_assets=list(labeled_sends),
                receive_assets=counter_receives,
                reasoning=(
                    f"Use {second_target['full_name']} as the more attainable lineup piece"
                    + (
                        f" while retaining the {nearest_first.label}."
                        if nearest_first is not None
                        else "."
                    )
                    + " This converts abstract surplus value into a named starting-lineup path."
                ),
            )
        if request.counterparty_roster_id is not None:
            rookie_pick_profile = RookiePickRepo(self._conn).get_profile(
                request.league_id,
                request.counterparty_roster_id,
            )
            pick_premium_sufficient = (
                rookie_pick_profile is not None
                and rookie_pick_profile.pick_premium_score is not None
                and rookie_pick_profile.pick_premium_score >= PICK_PREMIUM_THRESHOLD
                and (
                    rookie_pick_profile.pick_trade_evidence
                    + rookie_pick_profile.draft_selection_count
                )
                >= MIN_ROOKIE_PICK_EVIDENCE
            )
            if pick_premium_sufficient:
                has_pick_in_aggressive = any(
                    asset.asset_type == "pick"
                    for asset in aggressive_open.send_assets
                )
                if not has_pick_in_aggressive:
                    aggressive_open.reasoning = (
                        aggressive_open.reasoning
                        + " This manager consistently pays a premium for draft capital - "
                        + "consider adding a pick to improve acceptance odds."
                    )
        participant_offers = self._build_participant_offers(request, evaluation)
        return PackageBuilderResult(
            aggressive_open=aggressive_open,
            fair_close=fair_close,
            roster_fit_counter=roster_fit_counter,
            participant_offers=participant_offers or None,
        )

    def _build_counterparty_market_score(
        self,
        evaluation: TradeEvaluation,
    ) -> DimensionScore:
        score = round(100.0 - evaluation.market_fairness.score, 2)
        return DimensionScore(
            score=score,
            confidence=evaluation.market_fairness.confidence,
            reasoning="Counterparty view mirrors your net market score for the core swap.",
        )

    def _build_participant_offers(
        self,
        request: TradeRequest,
        evaluation: TradeEvaluation,
    ) -> list[ParticipantPackageOffer]:
        offers = [
            ParticipantPackageOffer(
                roster_id=request.user_roster_id,
                role="user",
                label="Your Net Package",
                send_assets=list(request.user_sends),
                receive_assets=list(request.user_receives),
                market_fairness=evaluation.market_fairness,
                reasoning=(
                    "Your package view scores everything you send and receive across the full deal."
                ),
            )
        ]
        if request.counterparty_roster_id is not None:
            offers.append(
                ParticipantPackageOffer(
                    roster_id=request.counterparty_roster_id,
                    role="primary_counterparty",
                    label=f"Roster {request.counterparty_roster_id} Core Package",
                    send_assets=list(request.user_receives),
                    receive_assets=list(request.user_sends),
                    market_fairness=self._build_counterparty_market_score(evaluation),
                    reasoning=(
                        "Primary counterparty package mirrors the core swap so the offer can be "
                        "explained from that manager's side, not only yours."
                    ),
                )
            )
        third_party_scores = {
            sidecar.roster_id: sidecar.market_fairness
            for sidecar in evaluation.third_party_evaluations or []
        }
        for leg in request.third_party_trades or []:
            market_fairness = third_party_scores.get(leg.roster_id)
            score_text = (
                f"{market_fairness.score:.1f}"
                if market_fairness is not None
                else "unscored"
            )
            offers.append(
                ParticipantPackageOffer(
                    roster_id=leg.roster_id,
                    role="third_party",
                    label=f"Roster {leg.roster_id} Sidecar Package",
                    send_assets=list(leg.sends),
                    receive_assets=list(leg.receives),
                    market_fairness=market_fairness,
                    reasoning=(
                        f"Uses the third-party sidecar market score ({score_text}) to explain "
                        "why this participant can accept its own send and receive leg."
                    ),
                )
            )
        return offers

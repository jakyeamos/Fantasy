from __future__ import annotations

import duckdb

from fantasy.rookie_pick.constants import (
    MIN_ROOKIE_PICK_EVIDENCE,
    PICK_PREMIUM_THRESHOLD,
)
from fantasy.rookie_pick.rookie_pick_repo import RookiePickRepo
from fantasy.trade.models import (
    PackageBuilderResult,
    PackageOffer,
    TradeEvaluation,
    TradeRequest,
)
from fantasy.trade.trade_repo import TradeRepo


class PackageBuilder:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._repo = TradeRepo(conn)

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
        fair_close = PackageOffer(
            label="Fair Close",
            send_assets=list(request.user_sends),
            receive_assets=list(request.user_receives),
            reasoning=(
                "Balances current market value with your roster direction without leaning too hard on the counterparty profile."
                if not request.third_party_trades
                else "Balances your net swap while the scored sidecar legs establish whether the extra team can accept the structure."
            ),
        )

        aggressive_sends = list(request.user_sends)
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
                + " Multi-team sidecar legs are scored separately; this open frames your primary ask."
            )
        aggressive_open = PackageOffer(
            label="Aggressive Open",
            send_assets=aggressive_sends,
            receive_assets=list(request.user_receives),
            reasoning=aggressive_reasoning,
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
        return PackageBuilderResult(
            aggressive_open=aggressive_open,
            fair_close=fair_close,
        )

from __future__ import annotations

import duckdb

from fantasy.trade.constants import MAX_REROUTES
from fantasy.trade.models import RerouteResult, TradeAsset, TradeEvaluation, TradeRequest
from fantasy.trade.trade_repo import TradeRepo


class RerouteEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._repo = TradeRepo(conn)

    def _primary_target(self, request: TradeRequest) -> TradeAsset | None:
        for asset in request.user_receives:
            if asset.asset_type == "player" and asset.player_id is not None:
                return asset
        return None

    def generate(
        self, request: TradeRequest, evaluation: TradeEvaluation
    ) -> list[RerouteResult]:
        reroutes: list[RerouteResult] = []
        if request.third_party_trades:
            return reroutes
        primary_target = self._primary_target(request)
        if primary_target is None or request.counterparty_roster_id is None:
            return reroutes

        counterparty_players = self._repo.get_roster_players(
            request.league_id, request.counterparty_roster_id
        )
        current_values = {
            row["player_id"]: row
            for row in self._repo.get_player_values(
                [player["player_id"] for player in counterparty_players],
                request.league_id,
                request.user_roster_id,
            )
        }
        target_value = current_values.get(primary_target.player_id or "")
        target_position = target_value.get("position") if target_value else None
        if target_position is not None:
            alternatives = [
                player
                for player in counterparty_players
                if player["position"] == target_position
                and player["player_id"] != primary_target.player_id
            ]
            ranked = sorted(
                alternatives,
                key=lambda item: (
                    float(current_values.get(item["player_id"], {}).get("lens_direction") or 0.0)
                    + float(current_values.get(item["player_id"], {}).get("lens_market") or 0.0)
                ),
                reverse=True,
            )
            for alternative in ranked[:2]:
                alternative_value = current_values.get(alternative["player_id"], {})
                reroutes.append(
                    RerouteResult(
                        reroute_type="better_target",
                        headline=f"Target {alternative['full_name']} instead",
                        reasoning=(
                            f"Higher direction-fit at {target_position} based on current market and fit lenses."
                        ),
                        suggested_assets=[
                            TradeAsset(
                                asset_type="player",
                                player_id=alternative["player_id"],
                            )
                        ],
                    )
                )

        if len(reroutes) < MAX_REROUTES and request.user_sends:
            current_send = next(
                (
                    asset
                    for asset in request.user_sends
                    if asset.asset_type == "player" and asset.player_id is not None
                ),
                None,
            )
            if current_send is not None:
                user_roster_players = self._repo.get_roster_players(
                    request.league_id, request.user_roster_id
                )
                user_values = {
                    row["player_id"]: row
                    for row in self._repo.get_player_values(
                        [player["player_id"] for player in user_roster_players],
                        request.league_id,
                        request.user_roster_id,
                    )
                }
                current_market = float(
                    user_values.get(current_send.player_id, {}).get("lens_market") or 0.0
                )
                cheaper = sorted(
                    [
                        player
                        for player in user_roster_players
                        if player["player_id"] != current_send.player_id
                        and float(user_values.get(player["player_id"], {}).get("lens_market") or 0.0)
                        < current_market
                    ],
                    key=lambda item: float(
                        user_values.get(item["player_id"], {}).get("lens_market") or 0.0
                    ),
                )
                if cheaper:
                    replacement = cheaper[0]
                    reroutes.append(
                        RerouteResult(
                            reroute_type="better_package",
                            headline=f"Send {replacement['full_name']} instead",
                            reasoning=(
                                f"This version keeps the same target while trimming the market cost from your side."
                            ),
                            suggested_assets=[
                                TradeAsset(
                                    asset_type="player",
                                    player_id=replacement["player_id"],
                                )
                            ],
                        )
                    )

        return reroutes[:MAX_REROUTES]

from __future__ import annotations

import json
from typing import Any, Literal
from urllib.parse import quote_plus

import duckdb

from fantasy.actions.models import TradeSuggestion
from fantasy.trade.models import TradeAsset, TradeRequest
from fantasy.trade.trade_engine import TradeEngine
from fantasy.trade.trade_repo import TradeRepo
from fantasy.trends.models import OpportunityFeedItem


class TradeSuggestionBuilder:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def build(self, item: OpportunityFeedItem) -> TradeSuggestion | None:
        if item.cta is None or item.cta.league_id is None or item.cta.user_roster_id is None:
            return None
        league_id = item.cta.league_id
        user_roster_id = item.cta.user_roster_id
        target_roster_id = item.cta.manager_roster_id or item.cta.target_player_roster_id
        if item.suggested_action == "buy":
            return self._buy_suggestion(item, league_id, user_roster_id, target_roster_id)
        return self._sell_suggestion(item, league_id, user_roster_id, target_roster_id)

    def destination(
        self,
        item: OpportunityFeedItem,
        suggestion: TradeSuggestion,
    ) -> str:
        if item.cta is None or item.cta.league_id is None:
            return "/opportunities"
        if item.cta.user_roster_id is None:
            return "/opportunities"
        return self.destination_for_suggestion(
            item.cta.league_id,
            item.cta.user_roster_id,
            suggestion,
        )

    def build_manager_suggestion(
        self,
        *,
        league_id: str,
        user_roster_id: int,
        target_roster_id: int,
        confidence: Literal["HIGH", "MEDIUM", "LOW"],
        manager_pitch_angle: str,
    ) -> TradeSuggestion | None:
        target_assets = self._roster_player_assets(league_id, target_roster_id)
        if not target_assets:
            return None
        target = target_assets[0]
        send_assets = self._select_send_assets(
            league_id,
            user_roster_id,
            target["player_id"],
            target["score"],
        )
        if not send_assets:
            return None
        receive_assets = [target]
        balancing = self._select_balancing_receive_asset(
            league_id,
            target_roster_id,
            target["player_id"],
            sum(asset["score"] for asset in send_assets) - target["score"],
        )
        if balancing is not None:
            receive_assets.append(balancing)
        suggestion = TradeSuggestion(
            league_id=league_id,
            target_player_id=target["player_id"],
            target_player_name=target["name"],
            target_manager_roster_id=target_roster_id,
            send_assets=[asset["label"] for asset in send_assets],
            receive_assets=[asset["label"] for asset in receive_assets],
            send_player_ids=[asset["player_id"] for asset in send_assets],
            receive_player_ids=[asset["player_id"] for asset in receive_assets],
            fairness_band=self._fairness_band(
                sum(asset["score"] for asset in send_assets),
                sum(asset["score"] for asset in receive_assets),
                confidence,
            ),
            acceptance_confidence=confidence,
            manager_pitch_angle=manager_pitch_angle,
        )
        return self._with_evaluation(suggestion, user_roster_id)

    def destination_for_suggestion(
        self,
        league_id: str,
        user_roster_id: int,
        suggestion: TradeSuggestion,
    ) -> str:
        params = [f"leagueId={league_id}", f"userRosterId={user_roster_id}"]
        if suggestion.target_manager_roster_id is not None:
            params.append(f"counterpartyRosterId={suggestion.target_manager_roster_id}")
        send_asset = self._query_asset(suggestion.send_player_ids[:1])
        receive_asset = self._query_asset(suggestion.receive_player_ids[:1])
        if send_asset is not None:
            params.extend(
                [
                    f"sendPlayerId={send_asset['player_id']}",
                    f"sendPlayerName={quote_plus(send_asset['name'])}",
                    f"sendPlayerPosition={quote_plus(send_asset['position'])}",
                ]
            )
        if receive_asset is not None:
            params.extend(
                [
                    f"receivePlayerId={receive_asset['player_id']}",
                    f"receivePlayerName={quote_plus(receive_asset['name'])}",
                    f"receivePlayerPosition={quote_plus(receive_asset['position'])}",
                    f"targetPlayerId={receive_asset['player_id']}",
                    f"targetPlayerName={quote_plus(receive_asset['name'])}",
                    f"targetPlayerPosition={quote_plus(receive_asset['position'])}",
                ]
            )
        return f"/trades?{'&'.join(params)}"

    def _buy_suggestion(
        self,
        item: OpportunityFeedItem,
        league_id: str,
        user_roster_id: int,
        target_roster_id: int | None,
    ) -> TradeSuggestion | None:
        target = self._player_asset(league_id, item.player_id, target_roster_id)
        send_assets = self._select_send_assets(
            league_id,
            user_roster_id,
            item.player_id,
            target["score"] if target else None,
        )
        if target is None or not send_assets:
            return None
        receive_assets = [target]
        balancing = self._select_balancing_receive_asset(
            league_id,
            target_roster_id,
            item.player_id,
            sum(asset["score"] for asset in send_assets) - target["score"],
        )
        if balancing is not None:
            receive_assets.append(balancing)
        suggestion = TradeSuggestion(
            league_id=league_id,
            target_player_id=item.player_id,
            target_player_name=item.player_name,
            target_manager_roster_id=target_roster_id,
            send_assets=[asset["label"] for asset in send_assets],
            receive_assets=[asset["label"] for asset in receive_assets],
            send_player_ids=[asset["player_id"] for asset in send_assets],
            receive_player_ids=[asset["player_id"] for asset in receive_assets],
            fairness_band=self._fairness_band(
                sum(asset["score"] for asset in send_assets),
                sum(asset["score"] for asset in receive_assets),
                item.trend_confidence,
            ),
            acceptance_confidence=item.trend_confidence,
            manager_pitch_angle=self._manager_pitch_angle(league_id, target_roster_id)
            or "Frame it as roster flexibility for them, not as a model discount for you.",
        )
        return self._with_evaluation(suggestion, user_roster_id)

    def _sell_suggestion(
        self,
        item: OpportunityFeedItem,
        league_id: str,
        user_roster_id: int,
        target_roster_id: int | None,
    ) -> TradeSuggestion | None:
        sell_target = self._player_asset(league_id, item.player_id, user_roster_id)
        if sell_target is None:
            return None
        receive_assets = self._select_receive_targets(
            league_id,
            user_roster_id,
            target_roster_id,
            item.position,
            sell_target["score"],
        )
        if not receive_assets:
            return None
        suggestion = TradeSuggestion(
            league_id=league_id,
            target_player_id=item.player_id,
            target_player_name=item.player_name,
            target_manager_roster_id=target_roster_id,
            send_assets=[sell_target["label"]],
            receive_assets=[asset["label"] for asset in receive_assets],
            send_player_ids=[sell_target["player_id"]],
            receive_player_ids=[asset["player_id"] for asset in receive_assets],
            fairness_band=self._fairness_band(
                sell_target["score"],
                sum(asset["score"] for asset in receive_assets),
                item.trend_confidence,
            ),
            acceptance_confidence=item.trend_confidence,
            manager_pitch_angle=self._manager_pitch_angle(league_id, target_roster_id)
            or "Sell the weekly certainty and make the return liquid enough to pivot again.",
        )
        return self._with_evaluation(suggestion, user_roster_id)

    def _with_evaluation(
        self,
        suggestion: TradeSuggestion,
        user_roster_id: int,
    ) -> TradeSuggestion:
        if not suggestion.send_player_ids or not suggestion.receive_player_ids:
            return suggestion
        request = TradeRequest(
            league_id=suggestion.league_id,
            user_roster_id=user_roster_id,
            counterparty_roster_id=suggestion.target_manager_roster_id,
            user_sends=[
                TradeAsset(asset_type="player", player_id=player_id)
                for player_id in suggestion.send_player_ids
            ],
            user_receives=[
                TradeAsset(asset_type="player", player_id=player_id)
                for player_id in suggestion.receive_player_ids
            ],
        )
        evaluation = TradeEngine(self._conn).evaluate(request)
        score = round(
            (
                evaluation.market_fairness.score
                + evaluation.direction_fit.score
                + evaluation.roster_fit.score
                + evaluation.timing_quality.score
            )
            / 4.0,
            2,
        )
        if score >= 58 and evaluation.market_fairness.score >= 42:
            verdict = "send"
        elif score >= 45:
            verdict = "counter"
        else:
            verdict = "avoid"
        return suggestion.model_copy(
            update={
                "evaluation_score": score,
                "evaluation_verdict": verdict,
                "evaluation_summary": (
                    f"{evaluation.strategic_distinction.headline}; package score {score:.1f}, "
                    f"market {evaluation.market_fairness.score:.1f}, "
                    f"direction {evaluation.direction_fit.score:.1f}."
                ),
            }
        )

    def _query_asset(self, player_ids: list[str]) -> dict[str, str] | None:
        if not player_ids:
            return None
        row = self._conn.execute(
            """
            SELECT player_id, COALESCE(full_name, player_id), COALESCE(position, 'UNKNOWN')
            FROM players
            WHERE player_id = ?
            LIMIT 1
            """,
            [player_ids[0]],
        ).fetchone()
        if row is None:
            return None
        return {"player_id": str(row[0]), "name": str(row[1]), "position": str(row[2])}

    def _player_asset(
        self,
        league_id: str,
        player_id: str,
        roster_id: int | None,
    ) -> dict[str, Any] | None:
        if roster_id is not None:
            for asset in self._roster_player_assets(league_id, roster_id):
                if asset["player_id"] == player_id:
                    return asset
        row = self._conn.execute(
            """
            SELECT p.player_id, COALESCE(p.full_name, p.player_id), COALESCE(p.position, 'UNKNOWN'),
                   COALESCE(pv.lens_market, pv.lens_production, pv.comp_current_production, 0.5)
            FROM players p
            LEFT JOIN player_values pv ON pv.league_id = ? AND pv.player_id = p.player_id
            WHERE p.player_id = ?
            LIMIT 1
            """,
            [league_id, player_id],
        ).fetchone()
        if row is None:
            return None
        return self._asset_dict(row[0], row[1], row[2], float(row[3] or 0.5) * 100.0)

    def _roster_player_assets(self, league_id: str, roster_id: int) -> list[dict[str, Any]]:
        row = self._conn.execute(
            """
            SELECT players
            FROM rosters
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            return []
        player_ids = [
            str(value)
            for value in json.loads(row[0] or "[]")
            if value not in (None, "", 0, "0")
        ]
        if not player_ids:
            return []
        rows = self._conn.execute(
            """
            WITH adp AS (
                SELECT player_id, MIN(adp) AS adp
                FROM player_adp_baseline
                GROUP BY player_id
            )
            SELECT p.player_id, COALESCE(p.full_name, p.player_id), COALESCE(p.position, 'UNKNOWN'),
                   COALESCE(
                       (
                           COALESCE(pv.lens_market, 0.5) * 0.30
                         + COALESCE(pv.lens_production, 0.5) * 0.25
                         + COALESCE(pv.comp_current_production, 0.5) * 0.20
                         + COALESCE(pv.comp_market_liquidity, 0.5) * 0.15
                         + COALESCE(pv.comp_ceiling, 0.5) * 0.10
                       ) * 100.0,
                       100.0 - LEAST(COALESCE(adp.adp, 150.0), 250.0) / 2.5
                   ) AS score
            FROM players p
            LEFT JOIN player_values pv
              ON pv.league_id = ? AND pv.roster_id = ? AND pv.player_id = p.player_id
            LEFT JOIN adp ON adp.player_id = p.player_id
            WHERE p.player_id IN (SELECT UNNEST(?))
            """,
            [league_id, roster_id, player_ids],
        ).fetchall()
        assets = [self._asset_dict(row[0], row[1], row[2], float(row[3] or 50.0)) for row in rows]
        assets.sort(key=lambda asset: (-asset["score"], asset["label"]))
        return assets

    def _asset_dict(
        self,
        player_id: object,
        name: object,
        position: object,
        score: float,
    ) -> dict[str, Any]:
        position_text = str(position)
        return {
            "player_id": str(player_id),
            "name": str(name),
            "label": f"{name} ({position_text})",
            "position": position_text,
            "score": max(1.0, min(100.0, score)),
        }

    def _select_send_assets(
        self,
        league_id: str,
        user_roster_id: int,
        excluded_player_id: str,
        target_score: float | None,
    ) -> list[dict[str, Any]]:
        target = target_score or 55.0
        candidates = [
            asset
            for asset in self._roster_player_assets(league_id, user_roster_id)
            if asset["player_id"] != excluded_player_id
        ]
        if not candidates:
            return []
        candidates.sort(key=lambda asset: (abs(asset["score"] - target * 0.82), -asset["score"]))
        selected = [candidates[0]]
        if selected[0]["score"] < target * 0.65:
            extras = [asset for asset in candidates[1:] if asset["score"] <= target * 0.45]
            if extras:
                selected.append(extras[0])
        return selected

    def _select_balancing_receive_asset(
        self,
        league_id: str,
        roster_id: int | None,
        excluded_player_id: str,
        surplus_score: float,
    ) -> dict[str, Any] | None:
        if roster_id is None or surplus_score < 12:
            return None
        candidates = [
            asset
            for asset in self._roster_player_assets(league_id, roster_id)
            if asset["player_id"] != excluded_player_id and asset["score"] <= surplus_score * 1.1
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda asset: abs(asset["score"] - surplus_score * 0.65))
        return candidates[0]

    def _select_receive_targets(
        self,
        league_id: str,
        user_roster_id: int,
        preferred_roster_id: int | None,
        position: str,
        sell_score: float,
    ) -> list[dict[str, Any]]:
        roster_ids = self._candidate_roster_ids(league_id, user_roster_id, preferred_roster_id)
        candidates: list[dict[str, Any]] = []
        for roster_id in roster_ids:
            candidates.extend(
                asset
                for asset in self._roster_player_assets(league_id, roster_id)
                if asset["position"] == position and asset["score"] <= sell_score * 1.05
            )
        candidates.sort(key=lambda asset: (abs(asset["score"] - sell_score * 0.82), -asset["score"]))
        return candidates[:1]

    def _candidate_roster_ids(
        self,
        league_id: str,
        user_roster_id: int,
        preferred_roster_id: int | None,
    ) -> list[int]:
        if preferred_roster_id is not None and preferred_roster_id != user_roster_id:
            return [preferred_roster_id]
        return [
            int(row[0])
            for row in self._conn.execute(
                """
                SELECT roster_id
                FROM rosters
                WHERE league_id = ? AND roster_id != ?
                ORDER BY roster_id
                """,
                [league_id, user_roster_id],
            ).fetchall()
        ]

    def _fairness_band(
        self,
        send_score: float,
        receive_score: float,
        confidence: str,
    ) -> Literal["underpay", "fair", "overpay", "unknown"]:
        ratio = send_score / max(receive_score, 1.0)
        if ratio < 0.82:
            return "underpay" if confidence == "HIGH" else "unknown"
        if ratio > 1.18:
            return "overpay"
        return "fair"

    def _manager_pitch_angle(self, league_id: str, roster_id: int | None) -> str | None:
        if roster_id is None:
            return None
        angles = TradeRepo(self._conn).get_pitch_angles(league_id, roster_id)
        if not angles:
            return None
        angle = angles[0]
        return (
            f"Open with {angle['send_description']}; avoid {angle['avoid_description']}. "
            f"{angle['reasoning']}"
        )

"""Trade Lab presentation and follow-up projections over append-only feedback."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import duckdb

from fantasy.decision.calibration import trade_calibration_evidence
from fantasy.decision.feedback_repo import DecisionFeedbackRepo
from fantasy.trade.models import (
    TradeAnalysis,
    TradeCalibrationEvidence,
    TradeFeedbackLink,
    TradeFollowUpEventRequest,
    TradeFollowUpEventResponse,
    TradeFollowUpRow,
    TradeFollowUpsResponse,
    TradeRequest,
)


def _canonical_asset(asset: Any) -> dict[str, Any]:
    return asset.model_dump(mode="json", exclude_none=True)


def _canonical_request(request: TradeRequest) -> dict[str, Any]:
    """Build a stable identity from the exact offer, excluding render flags."""

    sends = sorted(
        (_canonical_asset(asset) for asset in request.user_sends),
        key=lambda asset: json.dumps(asset, sort_keys=True, separators=(",", ":")),
    )
    receives = sorted(
        (_canonical_asset(asset) for asset in request.user_receives),
        key=lambda asset: json.dumps(asset, sort_keys=True, separators=(",", ":")),
    )
    third_party = []
    for leg in request.third_party_trades or []:
        third_party.append(
            {
                "roster_id": leg.roster_id,
                "sends": sorted(
                    (_canonical_asset(asset) for asset in leg.sends),
                    key=lambda asset: json.dumps(
                        asset, sort_keys=True, separators=(",", ":")
                    ),
                ),
                "receives": sorted(
                    (_canonical_asset(asset) for asset in leg.receives),
                    key=lambda asset: json.dumps(
                        asset, sort_keys=True, separators=(",", ":")
                    ),
                ),
            }
        )
    return {
        "league_id": request.league_id,
        "user_roster_id": request.user_roster_id,
        "counterparty_roster_id": request.counterparty_roster_id,
        "user_sends": sends,
        "user_receives": receives,
        "third_party_trades": sorted(third_party, key=lambda leg: leg["roster_id"]),
    }


def trade_decision_id(request: TradeRequest) -> str:
    canonical = json.dumps(
        _canonical_request(request),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"trade-{hashlib.sha256(canonical).hexdigest()[:24]}"


class TradeFeedbackService:
    """Adapt Trade Lab packets to the shared append-only decision lifecycle."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn
        self._repo = DecisionFeedbackRepo(conn)

    def _league_context(self, league_id: str) -> tuple[str | None, str | None]:
        row = self._conn.execute(
            "SELECT name, season FROM leagues WHERE league_id = ?",
            [league_id],
        ).fetchone()
        if row is None:
            return None, None
        return (
            str(row[0]) if row[0] is not None else None,
            str(row[1]) if row[1] is not None else None,
        )

    @staticmethod
    def _offer_question(analysis: TradeAnalysis) -> str:
        sends = [asset.label for asset in analysis.assets if asset.side == "user_send"]
        receives = [
            asset.label for asset in analysis.assets if asset.side == "user_receive"
        ]
        send_text = ", ".join(sends) or "the selected outgoing package"
        receive_text = ", ".join(receives) or "the selected incoming package"
        return f"Trade Lab offer: send {send_text} for {receive_text}."

    def _packet(
        self,
        request: TradeRequest,
        analysis: TradeAnalysis,
    ) -> dict[str, Any]:
        league_name, season = self._league_context(request.league_id)
        decision_id = trade_decision_id(request)
        return {
            "schema_version": "decision-packet/1.0",
            "decision_id": decision_id,
            "decision_type": "trade",
            "question": self._offer_question(analysis),
            "league": {
                "league_id": request.league_id,
                "league_name": league_name,
                "season": season,
                "roster_id": request.user_roster_id,
            },
            "recommendation": {
                "action": analysis.verdict,
                "confidence": round(analysis.model_score_point / 100.0, 4),
                "summary": analysis.headline,
            },
            "trade_request": _canonical_request(request),
            "trade_analysis": analysis.model_dump(mode="json"),
            "evidence": {
                "calibration": analysis.quality.calibration,
                "freshness": analysis.quality.freshness,
            },
            "limitations": analysis.quality.limitations,
        }

    @staticmethod
    def _link_from_history(
        decision_id: str,
        history: list[dict[str, Any]],
    ) -> TradeFeedbackLink:
        if not history:
            raise ValueError(f"No feedback history exists for {decision_id}.")
        presentation = next(
            (event for event in history if event["event_type"] == "presented"),
            None,
        )
        if presentation is None:
            raise ValueError(f"No presented Trade Lab decision exists for {decision_id}.")
        latest = history[-1]
        return TradeFeedbackLink(
            decision_id=decision_id,
            presentation_id=int(presentation["id"]),
            latest_event=str(latest["event_type"]),
            resolution_state=str(latest["resolution_state"]),
            follow_up_at=latest["follow_up_at"],
        )

    def present(
        self,
        request: TradeRequest,
        analysis: TradeAnalysis,
    ) -> TradeFeedbackLink:
        packet = self._packet(request, analysis)
        self._repo.record_presentation(packet)
        history = self._repo.list_feedback(packet["decision_id"])
        return self._link_from_history(packet["decision_id"], history)

    def calibration(self, league_id: str) -> TradeCalibrationEvidence:
        return TradeCalibrationEvidence(
            **trade_calibration_evidence(self._conn, league_id=league_id)
        )

    def _assert_trade_scope(self, decision_id: str, league_id: str) -> None:
        packet = self._repo.latest_packet(decision_id)
        packet_league = packet.get("league", {}).get("league_id") if packet else None
        if (
            packet is None
            or packet.get("decision_type") != "trade"
            or str(packet_league) != league_id
        ):
            raise LookupError(
                f"Trade Lab decision {decision_id} was not found in league {league_id}."
            )

    def list_follow_ups(self, league_id: str) -> TradeFollowUpsResponse:
        follow_ups: list[TradeFollowUpRow] = []
        for row in self._repo.list_unresolved(
            league_id=league_id,
            decision_type="trade",
        ):
            history = self._repo.list_feedback(row["decision_id"])
            presentation = next(
                (event for event in history if event["event_type"] == "presented"),
                None,
            )
            if presentation is None:
                continue
            follow_ups.append(
                TradeFollowUpRow(
                    decision_id=row["decision_id"],
                    presentation_id=int(presentation["id"]),
                    league_id=row["league_id"],
                    roster_id=row["roster_id"],
                    question=row["question"],
                    recommendation_action=row["recommendation_action"],
                    confidence=row["confidence"],
                    latest_event=row["latest_event"],
                    resolution_state=row["resolution_state"],
                    follow_up_at=row["follow_up_at"],
                    is_due=row["is_due"],
                    history=[
                        {
                            **event,
                        }
                        for event in history
                    ],
                )
            )
        league_name, _ = self._league_context(league_id)
        return TradeFollowUpsResponse(
            league_id=league_id,
            league_name=league_name,
            calibration=self.calibration(league_id),
            follow_ups=follow_ups,
        )

    def record_event(
        self,
        decision_id: str,
        league_id: str,
        event: TradeFollowUpEventRequest,
    ) -> TradeFollowUpEventResponse:
        self._assert_trade_scope(decision_id, league_id)
        if event.event_type == "outcome":
            if event.outcome is None:
                raise ValueError("Outcome check-ins require a correctness label.")
            outcome_score = 1.0 if event.outcome == "recommendation_correct" else 0.0
        else:
            if event.outcome is not None:
                raise ValueError("Correctness labels are only valid for outcome check-ins.")
            outcome_score = None

        event_id = self._repo.record_event(
            decision_id,
            event_type=event.event_type,
            outcome=event.outcome,
            outcome_score=outcome_score,
            follow_up_at=event.follow_up_at,
            notes=event.notes,
        )
        latest = self._repo.list_feedback(decision_id)[-1]
        return TradeFollowUpEventResponse(
            decision_id=decision_id,
            event_id=event_id,
            event_type=event.event_type,
            resolution_state=latest["resolution_state"],
            follow_up_at=latest["follow_up_at"],
            calibration=self.calibration(league_id),
        )

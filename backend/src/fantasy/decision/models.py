from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OfferInterpretation(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["underspecified", "partially_specified", "specified", "not_applicable"]
    parsed_assets: list[dict[str, Any]] = Field(default_factory=list)
    missing_details: list[str] = Field(default_factory=list)


class DecisionRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True)

    action: Literal[
        "request_details",
        "hold_pending_evaluation",
        "consider",
        "decline",
        "insufficient_context",
    ]
    summary: str
    confidence: float
    confidence_basis: str
    minimum_return: list[str] = Field(default_factory=list)
    why: list[str] = Field(default_factory=list)
    downside: str
    contrary_case: str
    what_changes_the_answer: list[str] = Field(default_factory=list)


class DecisionPacket(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["decision-packet/1.0"] = "decision-packet/1.0"
    decision_id: str
    decision_type: str
    question: str
    subject: dict[str, Any] | None
    league: dict[str, Any]
    interpretation: OfferInterpretation
    recommendation: DecisionRecommendation
    evidence: dict[str, Any]
    limitations: list[str] = Field(default_factory=list)

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

import duckdb


@dataclass(frozen=True)
class PortfolioPlayerRisk:
    availability_status: Literal["monitor", "out"]
    recommended_action: str
    why_now: str
    risk_if_wrong: str
    evidence: list[str]
    stale_domains: list[str]
    urgency: Literal["today", "this_week"]
    confidence: Literal["HIGH", "MEDIUM"]


def _loads(raw: str | None) -> dict[str, object]:
    if raw is None:
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def portfolio_player_risk(
    conn: duckdb.DuckDBPyConnection,
    player_id: str,
    player_name: str,
) -> PortfolioPlayerRisk | None:
    row = conn.execute(
        """
        SELECT metadata_blob
        FROM players
        WHERE player_id = ?
        LIMIT 1
        """,
        [player_id],
    ).fetchone()
    metadata = _loads(str(row[0]) if row and row[0] is not None else None)
    status = str(
        metadata.get("injury_status") or metadata.get("status") or ""
    ).strip().lower()
    if status in {"out", "doubtful", "ir", "injured reserve"}:
        return PortfolioPlayerRisk(
            availability_status="out",
            recommended_action=(
                f"Hedge {player_name} now: shop one share or add a direct backup plan before lineups lock."
            ),
            why_now=(
                f"{player_name} is a portfolio-level concentration and availability is out."
            ),
            risk_if_wrong=(
                "Hedging an injured player can cost upside if availability clears faster than the market expects."
            ),
            evidence=[
                "Availability: out",
                "News dependency: confirm injury status before locking portfolio exposure",
            ],
            stale_domains=["injuries"],
            urgency="today",
            confidence="HIGH",
        )
    if status in {"questionable", "limited"}:
        return PortfolioPlayerRisk(
            availability_status="monitor",
            recommended_action=(
                f"Prepare a hedge plan for {player_name}; do not add more exposure until status clears."
            ),
            why_now=(
                f"{player_name} is a portfolio-level concentration with active availability uncertainty."
            ),
            risk_if_wrong=(
                "The status tag may resolve before lineups lock, making a hedge unnecessary."
            ),
            evidence=[
                "Availability: monitor",
                "News dependency: confirm injury status before locking portfolio exposure",
            ],
            stale_domains=["injuries"],
            urgency="this_week",
            confidence="MEDIUM",
        )
    return None

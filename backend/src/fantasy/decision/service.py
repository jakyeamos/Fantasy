from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import duckdb

from fantasy.decision.calibration import calibration_evidence
from fantasy.decision.models import (
    DecisionPacket,
    DecisionRecommendation,
    OfferInterpretation,
)


_ROUND_MAP = {
    "1st": 1,
    "first": 1,
    "2nd": 2,
    "second": 2,
    "3rd": 3,
    "third": 3,
    "4th": 4,
    "fourth": 4,
}


def _optional_row(
    conn: duckdb.DuckDBPyConnection, query: str, params: list[Any]
) -> tuple[Any, ...] | None:
    try:
        return conn.execute(query, params).fetchone()
    except duckdb.Error:
        return None


def _parse_offer(question: str) -> OfferInterpretation:
    lower = question.lower()
    if "pick" not in lower and not any(token in lower.split() for token in _ROUND_MAP):
        return OfferInterpretation(status="not_applicable")
    pattern = re.compile(
        r"(?:(20\d{2})\s+)?(?:(early|mid|late)\s+)?(1st|first|2nd|second|3rd|third|4th|fourth)"
    )
    assets = [
        {
            "asset_type": "rookie_pick",
            "year": int(match.group(1)) if match.group(1) else None,
            "projected_range": match.group(2),
            "round": _ROUND_MAP[match.group(3)],
        }
        for match in pattern.finditer(lower)
    ]
    if not assets:
        return OfferInterpretation(
            status="underspecified",
            missing_details=["pick years", "pick rounds", "projected pick ranges"],
        )
    missing: list[str] = []
    if any(asset["year"] is None for asset in assets):
        missing.append("pick years")
    if any(asset["projected_range"] is None for asset in assets):
        missing.append("projected pick ranges")
    return OfferInterpretation(
        status="partially_specified" if missing else "specified",
        parsed_assets=assets,
        missing_details=missing,
    )


def _lineup_evidence(
    conn: duckdb.DuckDBPyConnection, league_id: str, roster_id: int
) -> dict[str, Any]:
    row = _optional_row(
        conn,
        """
        SELECT title_window_label, title_window_composite, total_lineup_score,
               overall_gap_to_title_target, overall_benchmark_source,
               overall_benchmark_sample_size, CAST(computed_at AS VARCHAR),
               recommendation_cards_json
        FROM lineup_scores
        WHERE league_id = ? AND roster_id = ?
        LIMIT 1
        """,
        [league_id, roster_id],
    )
    if not row:
        return {"status": "unavailable"}
    return {
        "status": "available",
        "title_window_label": str(row[0]),
        "title_window_composite": float(row[1]),
        "total_lineup_score": float(row[2]),
        "gap_to_title_target": float(row[3]),
        "benchmark_source": str(row[4]),
        "benchmark_sample_size": int(row[5]),
        "computed_at": str(row[6]),
        "recommendation_cards": json.loads(row[7] or "[]"),
    }


def _player_value_evidence(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    roster_id: int,
    player_id: str | None,
) -> dict[str, Any]:
    if not player_id:
        return {"status": "not_applicable"}
    row = _optional_row(
        conn,
        """
        SELECT lens_production, lens_market, lens_insulation, lens_team_fit,
               lens_direction, comp_positional_scarcity, comp_fragility,
               CAST(computed_at AS VARCHAR)
        FROM player_values
        WHERE league_id = ? AND roster_id = ? AND player_id = ?
        LIMIT 1
        """,
        [league_id, roster_id, player_id],
    )
    if not row:
        return {"status": "unavailable"}
    return {
        "status": "available",
        "production": float(row[0]),
        "market": float(row[1]),
        "insulation": float(row[2]),
        "team_fit": float(row[3]),
        "direction": float(row[4]),
        "positional_scarcity": float(row[5]),
        "fragility": float(row[6]),
        "computed_at": str(row[7]),
    }


def _format_evidence(
    conn: duckdb.DuckDBPyConnection, league_id: str, league: dict[str, Any]
) -> dict[str, Any]:
    row = _optional_row(
        conn,
        """
        SELECT acknowledged_rules, CAST(acknowledged_at AS VARCHAR)
        FROM league_format_acknowledgments WHERE league_id = ? LIMIT 1
        """,
        [league_id],
    )
    return {
        "superflex": bool(league.get("superflex")),
        "tep": bool(league.get("tep")),
        "ppr": float(league.get("ppr", 0)),
        "acknowledgment": (
            {"status": "available", "rules": json.loads(row[0]), "acknowledged_at": str(row[1])}
            if row
            else {"status": "unavailable"}
        ),
    }


def _pick_inventory(roster: dict[str, Any]) -> dict[str, Any]:
    picks = roster.get("picks_owned", [])
    firsts = [
        pick for pick in picks
        if int(pick.get("round", pick.get("pick_round", 0)) or 0) == 1
    ]
    return {
        "total_picks": len(picks),
        "first_round_picks": len(firsts),
        "first_round_surplus": len(firsts) >= 4,
    }


def _roster_recommendation(
    *,
    roster: dict[str, Any],
    team_direction: dict[str, Any] | None,
    team_scorecard: dict[str, Any] | None,
    lineup: dict[str, Any],
    data_health: dict[str, Any],
    calibration: dict[str, Any],
) -> DecisionRecommendation:
    """Return a bounded strategy recommendation when the subject is a roster."""

    qbs = [entry for entry in roster.get("players", []) if entry.get("position") == "QB"]
    inventory = _pick_inventory(roster)
    direction_label = (
        str(team_direction.get("primary_label"))
        if team_direction and team_direction.get("primary_label")
        else "current roster"
    )
    why = [
        f"The roster currently carries {len(qbs)} quarterbacks and "
        f"{inventory['first_round_picks']} first-round picks.",
        f"The stored team direction is {direction_label}.",
    ]
    if team_scorecard is not None:
        why.append("A persisted team scorecard is available for depth, age-risk, and flexibility checks.")
    if lineup.get("status") == "available":
        why.append("Persisted lineup evidence is available for the roster.")

    limitations: list[str] = []
    if data_health.get("status") != "valid":
        limitations.append("stats health is degraded")
    if calibration.get("status") != "available":
        limitations.append("decision confidence is uncalibrated")
    if lineup.get("status") != "available":
        limitations.append("persisted lineup evidence is unavailable")
    confidence = max(0.35, 0.62 - (0.08 * len(limitations)))
    return DecisionRecommendation(
        action="consider",
        summary=(
            f"Use a roster-level plan under the {direction_label} direction: preserve the "
            "strongest core, identify the weakest starting or depth position, and spend "
            "premium assets only on a clear upgrade."
        ),
        confidence=round(confidence, 2),
        confidence_basis=(
            "Roster, league format, pick inventory, and persisted team evidence are grounded locally; "
            + (", ".join(limitations) if limitations else "configured evidence domains are available")
            + "."
        ),
        why=why,
        downside=(
            "Without a named player, pick package, or waiver target, a broad plan can miss "
            "a position-specific fit or cause an unnecessary overpay."
        ),
        contrary_case=(
            "If a specific player or offer creates an immediate starting-lineup edge, evaluate "
            "that asset directly instead of following the generic roster plan."
        ),
        what_changes_the_answer=[
            "A named player, pick package, or waiver target",
            "The expected lineup after the proposed move",
            "Exact pick years, rounds, and projected ranges",
            "A fresh league ingest and validated stats layer",
        ],
    )


def _recommendation(
    *,
    interpretation: OfferInterpretation,
    player: dict[str, Any] | None,
    subject: dict[str, Any] | None,
    league: dict[str, Any],
    roster: dict[str, Any],
    market: dict[str, Any],
    team_direction: dict[str, Any] | None,
    team_scorecard: dict[str, Any] | None,
    lineup: dict[str, Any],
    data_health: dict[str, Any],
    calibration: dict[str, Any],
) -> DecisionRecommendation:
    if subject and subject.get("subject_type") == "roster":
        return _roster_recommendation(
            roster=roster,
            team_direction=team_direction,
            team_scorecard=team_scorecard,
            lineup=lineup,
            data_health=data_health,
            calibration=calibration,
        )
    if player is None:
        return DecisionRecommendation(
            action="insufficient_context",
            summary="No decision subject was resolved from local player data.",
            confidence=0.0,
            confidence_basis="No player entity matched.",
            downside="A generic recommendation could target the wrong asset.",
            contrary_case="A resolved player or asset would make evaluation possible.",
            what_changes_the_answer=["Provide a player or pick asset present in the local database."],
        )

    adp = (market.get("adp_baseline") or {}).get("adp")
    elite_sf_qb = (
        bool(league.get("superflex"))
        and player.get("position") == "QB"
        and adp is not None
        and float(adp) <= 24
    )
    qbs = [entry for entry in roster.get("players", []) if entry.get("position") == "QB"]
    inventory = _pick_inventory(roster)
    minimum = (
        [
            "At least two first-round-equivalent assets",
            "At least one premium or plausibly early first-round asset",
            "No return made only of distant projected-mid picks",
        ]
        if elite_sf_qb
        else ["A return that clears the player's current dynasty acquisition cost"]
    )
    why = [
        f"The league is {'superflex' if league.get('superflex') else 'one-QB'}, which materially changes QB scarcity.",
        f"The roster currently carries {len(qbs)} quarterbacks and {inventory['first_round_picks']} first-round picks.",
    ]
    if adp is not None:
        why.append(f"The local ADP baseline is {float(adp):g}.")
    if inventory["first_round_surplus"]:
        why.append("The roster already has a first-round-pick surplus, reducing the value of another generic reroll.")

    limitations: list[str] = []
    if market.get("market_value") is None:
        limitations.append("live market value is missing")
    if data_health.get("status") != "valid":
        limitations.append("stats health is degraded")
    if calibration.get("status") != "available":
        limitations.append("decision confidence is uncalibrated")
    confidence = max(0.35, 0.76 - (0.08 * len(limitations)))

    if interpretation.status in {"underspecified", "partially_specified"}:
        action = "request_details"
        summary = (
            f"Do not accept an unspecified picks-only offer for {player['full_name']}. "
            "Get the years, rounds, and projected ranges, then compare the package with the reservation threshold."
        )
    else:
        action = "hold_pending_evaluation"
        summary = (
            f"Hold {player['full_name']} pending an asset-by-asset trade evaluation; "
            "the parsed offer alone is not enough to establish the counterparty and ownership chain."
        )
    return DecisionRecommendation(
        action=action,
        summary=summary,
        confidence=round(confidence, 2),
        confidence_basis=(
            "Roster, league format, pick inventory, and ADP are grounded locally; "
            + (", ".join(limitations) if limitations else "all configured evidence domains are available")
            + "."
        ),
        minimum_return=minimum,
        why=why,
        downside="Trading an elite scarce asset for fungible picks can create value without replacing weekly lineup leverage.",
        contrary_case="A clearly rebuilding roster with weak quarterback insulation can prefer liquid picks if the package materially exceeds replacement cost.",
        what_changes_the_answer=[
            "Exact pick years and rounds",
            "Projected early, mid, or late ranges",
            "The counterparty and current pick ownership",
            "A current external market value",
            "A calibrated historical outcome sample",
        ],
    )


def build_decision_packet(
    conn: duckdb.DuckDBPyConnection,
    *,
    question: str,
    player: dict[str, Any] | None,
    league_context: dict[str, Any],
    subject: dict[str, Any] | None = None,
) -> dict[str, Any]:
    league = league_context["league"]
    roster = league_context["roster"]
    league_id = str(league["league_id"])
    roster_id = int(roster["roster_id"])
    packet_subject = subject or ({"subject_type": "player", **player} if player else None)
    subject_type = packet_subject.get("subject_type") if packet_subject else None
    interpretation = (
        OfferInterpretation(status="not_applicable")
        if subject_type == "roster"
        else _parse_offer(question)
    )
    calibration = calibration_evidence(conn)
    market = {
        "market_value": player.get("market_value") if player else None,
        "adp_baseline": player.get("adp_baseline") if player else None,
    }
    evidence = {
        "data_health": league_context.get("data_health", {"status": "unknown"}),
        "format": _format_evidence(conn, league_id, league),
        "pick_inventory": _pick_inventory(roster),
        "team_direction": league_context.get("team_direction"),
        "team_scorecard": league_context.get("team_scorecard"),
        "lineup": _lineup_evidence(conn, league_id, roster_id),
        "player_value": _player_value_evidence(
            conn, league_id, roster_id, player.get("player_id") if player else None
        ),
        "market": market,
        "calibration": calibration,
    }
    recommendation = _recommendation(
        interpretation=interpretation,
        player=player,
        subject=packet_subject,
        league=league,
        roster=roster,
        market=market,
        team_direction=league_context.get("team_direction"),
        team_scorecard=league_context.get("team_scorecard"),
        lineup=evidence["lineup"],
        data_health=evidence["data_health"],
        calibration=calibration,
    )
    subject_identity = subject_type or "unresolved"
    identity = "|".join(
        [
            question.strip().lower(),
            league_id,
            str(roster_id),
            subject_identity,
            str(player and player.get("player_id")),
        ]
    )
    limitations = [
        value
        for value, condition in [
            ("Market value unavailable; ADP is a secondary proxy.", market["market_value"] is None),
            ("No calibrated historical decision sample is available.", calibration["status"] != "available"),
            ("Lineup evidence has not been persisted for this roster.", evidence["lineup"]["status"] != "available"),
            ("Player value lenses have not been persisted for this roster.", evidence["player_value"]["status"] == "unavailable"),
        ]
        if condition
    ]
    return DecisionPacket(
        decision_id=hashlib.sha256(identity.encode()).hexdigest()[:20],
        decision_type=(
            "roster"
            if subject_type == "roster"
            else "trade"
            if "trade" in question.lower() or " for " in question.lower()
            else "roster"
        ),
        question=question,
        subject=packet_subject,
        league={
            "league_id": league_id,
            "name": league["name"],
            "season": league["season"],
            "roster_id": roster_id,
        },
        interpretation=interpretation,
        recommendation=recommendation,
        evidence=evidence,
        limitations=limitations,
    ).model_dump()

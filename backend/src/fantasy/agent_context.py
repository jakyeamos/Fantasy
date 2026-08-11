"""Read-only, machine-readable context for repository-grounded fantasy advice."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

from fantasy.config import get_settings
from fantasy.data_health import assess_stats_health
from fantasy.decision import build_decision_packet
from fantasy.picks.pick_engine import PickEngine
from fantasy.picks.pick_repo import PickRepo

DECISION_TERMS = {
    "add",
    "buy",
    "drop",
    "dynasty",
    "first",
    "1st",
    "league",
    "lineup",
    "pick",
    "picks",
    "roster",
    "sell",
    "second",
    "2nd",
    "sit",
    "standings",
    "start",
    "team",
    "trade",
    "waiver",
    "waivers",
}

ROSTER_SCOPE_MARKERS = (
    "my team",
    "my roster",
    "entire roster",
    "whole roster",
    "holistic",
    "overall strategy",
    "team direction",
    "roster construction",
    "lineup construction",
    "what moves should i make",
    "what should i do with my",
    "should i rebuild",
    "should i contend",
)


@dataclass(frozen=True)
class OwnerSelector:
    kind: str
    value: str
    source: str


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return fallback


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="seconds") + ("Z" if value.tzinfo is None else "")


def should_ground_question(question: str) -> bool:
    """Return whether a natural-language question calls for private league context."""

    words = {
        token.strip(".,?!:;()[]{}\"'").lower()
        for token in question.split()
    }
    return bool(words & DECISION_TERMS)


def should_use_roster_subject(question: str) -> bool:
    """Return whether a decision question explicitly asks for roster-level guidance."""

    normalized = " ".join(question.lower().split())
    return any(marker in normalized for marker in ROSTER_SCOPE_MARKERS)


def _resolve_owner_selector(
    owner_id: str | None,
    owner_display_name: str | None,
) -> OwnerSelector | None:
    settings = get_settings()
    if owner_id:
        return OwnerSelector("owner_id", owner_id, "argument")
    if owner_display_name:
        return OwnerSelector("owner_display_name", owner_display_name, "argument")
    if settings.PORTFOLIO_OWNER_ID:
        return OwnerSelector("owner_id", settings.PORTFOLIO_OWNER_ID, "environment")
    if settings.PORTFOLIO_OWNER_DISPLAY_NAME:
        return OwnerSelector(
            "owner_display_name",
            settings.PORTFOLIO_OWNER_DISPLAY_NAME,
            "environment",
        )
    return None


def _detect_player(
    conn: duckdb.DuckDBPyConnection,
    *,
    player_query: str | None,
    question: str | None,
) -> dict[str, Any] | None:
    if player_query:
        row = conn.execute(
            """
            SELECT player_id, full_name, position, team, age, refreshed_at
            FROM players
            WHERE lower(full_name) = lower(?)
               OR lower(full_name) LIKE '%' || lower(?) || '%'
            ORDER BY
                CASE WHEN lower(full_name) = lower(?) THEN 0 ELSE 1 END,
                length(full_name),
                player_id
            LIMIT 1
            """,
            [player_query, player_query, player_query],
        ).fetchone()
    elif question:
        row = conn.execute(
            """
            SELECT player_id, full_name, position, team, age, refreshed_at
            FROM players
            WHERE lower(?) LIKE '%' || lower(full_name) || '%'
            ORDER BY length(full_name) DESC, player_id
            LIMIT 1
            """,
            [question],
        ).fetchone()
    else:
        row = None

    if row is None:
        return None
    return {
        "player_id": str(row[0]),
        "full_name": str(row[1] or row[0]),
        "position": str(row[2]) if row[2] is not None else None,
        "team": str(row[3]) if row[3] is not None else None,
        "age": int(row[4]) if row[4] is not None else None,
        "refreshed_at": _iso(row[5]),
    }


def _owner_rosters(
    conn: duckdb.DuckDBPyConnection,
    selector: OwnerSelector,
    league_id: str | None,
) -> list[tuple[Any, ...]]:
    selector_column = (
        "r.owner_id" if selector.kind == "owner_id" else "lower(r.owner_display_name)"
    )
    selector_value = selector.value if selector.kind == "owner_id" else selector.value.lower()
    league_clause = " AND r.league_id = ?" if league_id else ""
    params: list[Any] = [selector_value]
    if league_id:
        params.append(league_id)
    return conn.execute(
        f"""
        SELECT
            r.league_id,
            r.roster_id,
            r.owner_id,
            r.owner_display_name,
            r.players,
            r.starters,
            r.reserve,
            r.taxi,
            r.ingested_at
        FROM rosters r
        WHERE {selector_column} = ?{league_clause}
        ORDER BY r.league_id, r.roster_id
        """,
        params,
    ).fetchall()


def _roster_players(
    conn: duckdb.DuckDBPyConnection,
    players_raw: str | None,
    starters_raw: str | None,
    reserve_raw: str | None,
    taxi_raw: str | None,
) -> list[dict[str, Any]]:
    player_ids = [
        str(value)
        for value in _loads(players_raw, [])
        if value not in (None, "", 0, "0")
    ]
    if not player_ids:
        return []
    starters = {str(value) for value in _loads(starters_raw, [])}
    reserve = {str(value) for value in _loads(reserve_raw, [])}
    taxi = {str(value) for value in _loads(taxi_raw, [])}
    rows = conn.execute(
        """
        SELECT player_id, full_name, position, team, age
        FROM players
        WHERE player_id IN (SELECT UNNEST(?))
        ORDER BY
            CASE position
                WHEN 'QB' THEN 1
                WHEN 'RB' THEN 2
                WHEN 'WR' THEN 3
                WHEN 'TE' THEN 4
                ELSE 5
            END,
            full_name,
            player_id
        """,
        [player_ids],
    ).fetchall()
    return [
        {
            "player_id": str(row[0]),
            "full_name": str(row[1] or row[0]),
            "position": str(row[2]) if row[2] is not None else None,
            "team": str(row[3]) if row[3] is not None else None,
            "age": int(row[4]) if row[4] is not None else None,
            "starter": str(row[0]) in starters,
            "reserve": str(row[0]) in reserve,
            "taxi": str(row[0]) in taxi,
        }
        for row in rows
    ]


def _optional_row(
    conn: duckdb.DuckDBPyConnection,
    query: str,
    params: list[Any],
) -> tuple[Any, ...] | None:
    try:
        return conn.execute(query, params).fetchone()
    except duckdb.Error:
        return None


def _freshness(
    completed_at: datetime | None,
    *,
    now: datetime,
    stale_after_hours: float,
) -> dict[str, Any]:
    if completed_at is None:
        return {
            "status": "missing",
            "completed_at": None,
            "age_hours": None,
            "stale_after_hours": stale_after_hours,
        }
    comparable_now = now.replace(tzinfo=None) if now.tzinfo else now
    age_hours = max(0.0, (comparable_now - completed_at).total_seconds() / 3600)
    return {
        "status": "stale" if age_hours > stale_after_hours else "fresh",
        "completed_at": _iso(completed_at),
        "age_hours": round(age_hours, 2),
        "stale_after_hours": stale_after_hours,
    }


def _league_context(
    conn: duckdb.DuckDBPyConnection,
    roster_row: tuple[Any, ...],
    *,
    now: datetime,
    stale_after_hours: float,
) -> dict[str, Any]:
    league_id = str(roster_row[0])
    roster_id = int(roster_row[1])
    league = conn.execute(
        """
        SELECT name, season, superflex, tep, ppr, roster_positions, settings_blob, ingested_at
        FROM leagues
        WHERE league_id = ?
        LIMIT 1
        """,
        [league_id],
    ).fetchone()
    if league is None:
        raise ValueError(f"Roster references missing league {league_id}")

    settings_blob = _loads(league[6], {})
    standings = _optional_row(
        conn,
        """
        SELECT wins, losses, ties, fpts, fpts_against, ingested_at
        FROM standings
        WHERE league_id = ? AND roster_id = ?
        LIMIT 1
        """,
        [league_id, roster_id],
    )
    direction = _optional_row(
        conn,
        """
        SELECT primary_label, confidence, reasoning, approved_moves,
               discouraged_moves, computed_at
        FROM team_directions
        WHERE league_id = ? AND roster_id = ?
        ORDER BY computed_at DESC
        LIMIT 1
        """,
        [league_id, roster_id],
    )
    scorecard = _optional_row(
        conn,
        """
        SELECT win_now, future_value, depth, pick_capital, flexibility,
               fragility, age_risk, liquidity, positional_insulation,
               composite, computed_at
               , computation_json
        FROM team_scorecards
        WHERE league_id = ? AND roster_id = ?
        ORDER BY computed_at DESC
        LIMIT 1
        """,
        [league_id, roster_id],
    )
    ingest = _optional_row(
        conn,
        """
        SELECT run_type, completed_at
        FROM ingest_runs
        WHERE league_id = ? AND status = 'complete' AND completed_at IS NOT NULL
        ORDER BY completed_at DESC
        LIMIT 1
        """,
        [league_id],
    )
    completed_at = ingest[1] if ingest else league[7]
    ingest_freshness = _freshness(
        completed_at,
        now=now,
        stale_after_hours=stale_after_hours,
    )
    stats_health = assess_stats_health(conn, int(league[1])).model_dump()
    stats_health["semantic_status"] = (
        "stale"
        if ingest_freshness["status"] == "stale"
        else stats_health["status"]
    )

    picks: list[dict[str, Any]] = []
    try:
        pick_repo = PickRepo(conn)
        owned_picks = pick_repo.get_all_picks(league_id, roster_id)
        values = PickEngine(conn).compute_batch(owned_picks, league_id)
        for pick, value in zip(owned_picks, values, strict=True):
            payload = pick.model_dump()
            original_owner_id = payload.get("pick_owner_roster_id")
            payload["original_owner_name"] = (
                pick_repo.get_pick_owner_name(league_id, int(original_owner_id))
                if original_owner_id is not None
                else None
            )
            payload["valuation"] = value.model_dump(mode="json", exclude={"pick"})
            if value.rule_citation is not None:
                projected_slot = max(1, round(value.expected_draft_slot))
                payload["projected_slot"] = (
                    f"~{int(pick.pick_round or 1)}.{projected_slot:02d}"
                )
            picks.append(payload)
    except duckdb.Error:
        picks = []

    return {
        "league": {
            "league_id": league_id,
            "name": str(league[0]),
            "season": str(league[1]),
            "superflex": bool(league[2]),
            "tep": bool(league[3]),
            "ppr": float(league[4]),
            "num_teams": int(settings_blob.get("num_teams", 0) or 0),
            "draft_rounds": int(settings_blob.get("draft_rounds", 0) or 0),
            "roster_positions": _loads(league[5], []),
        },
        "roster": {
            "roster_id": roster_id,
            "owner_id": str(roster_row[2]) if roster_row[2] is not None else None,
            "owner_display_name": (
                str(roster_row[3]) if roster_row[3] is not None else None
            ),
            "players": _roster_players(
                conn,
                roster_row[4],
                roster_row[5],
                roster_row[6],
                roster_row[7],
            ),
            "picks_owned": picks,
        },
        "standings": (
            {
                "wins": int(standings[0]),
                "losses": int(standings[1]),
                "ties": int(standings[2]),
                "fpts": float(standings[3]),
                "fpts_against": float(standings[4]),
                "ingested_at": _iso(standings[5]),
            }
            if standings
            else None
        ),
        "team_direction": (
            {
                "primary_label": str(direction[0]),
                "confidence": float(direction[1]),
                "reasoning": str(direction[2]),
                "approved_moves": _loads(direction[3], []),
                "discouraged_moves": _loads(direction[4], []),
                "computed_at": _iso(direction[5]),
            }
            if direction
            else None
        ),
        "team_scorecard": (
            {
                "win_now": float(scorecard[0]),
                "future_value": float(scorecard[1]),
                "depth": float(scorecard[2]),
                "pick_capital": float(scorecard[3]),
                "flexibility": float(scorecard[4]),
                "fragility": float(scorecard[5]),
                "age_risk": float(scorecard[6]),
                "liquidity": float(scorecard[7]),
                "positional_insulation": float(scorecard[8]),
                "composite": float(scorecard[9]),
                "computed_at": _iso(scorecard[10]),
                "semantics": _loads(scorecard[11], {}),
            }
            if scorecard
            else None
        ),
        "ingest": {
            "run_type": str(ingest[0]) if ingest else None,
            **ingest_freshness,
        },
        "data_health": stats_health,
    }


def _player_market_context(
    conn: duckdb.DuckDBPyConnection,
    player_id: str,
) -> dict[str, Any]:
    market = _optional_row(
        conn,
        """
        SELECT fantasycalc_value, fantasycalc_rank, fantasycalc_trend30,
               adp_baseline, fetched_at
        FROM market_values
        WHERE player_id = ?
        ORDER BY fetched_at DESC
        LIMIT 1
        """,
        [player_id],
    )
    adp = _optional_row(
        conn,
        """
        SELECT adp, adp_source, loaded_at
        FROM player_adp_baseline
        WHERE player_id = ?
        ORDER BY loaded_at DESC
        LIMIT 1
        """,
        [player_id],
    )
    return {
        "market_value": (
            {
                "fantasycalc_value": (
                    float(market[0]) if market[0] is not None else None
                ),
                "fantasycalc_rank": int(market[1]) if market[1] is not None else None,
                "fantasycalc_trend30": (
                    float(market[2]) if market[2] is not None else None
                ),
                "adp_baseline": float(market[3]) if market[3] is not None else None,
                "fetched_at": _iso(market[4]),
            }
            if market
            else None
        ),
        "adp_baseline": (
            {
                "adp": float(adp[0]),
                "source": str(adp[1]) if adp[1] is not None else None,
                "loaded_at": _iso(adp[2]),
            }
            if adp
            else None
        ),
    }


def _roster_subject(league_context: dict[str, Any]) -> dict[str, Any]:
    """Build the stable subject identity for a roster-level decision packet."""

    league = league_context["league"]
    roster = league_context["roster"]
    return {
        "subject_type": "roster",
        "league_id": league["league_id"],
        "league_name": league["name"],
        "roster_id": roster["roster_id"],
        "owner_id": roster.get("owner_id"),
        "owner_display_name": roster.get("owner_display_name"),
    }


def build_agent_context(
    conn: duckdb.DuckDBPyConnection,
    *,
    question: str | None = None,
    player_query: str | None = None,
    owner_id: str | None = None,
    owner_display_name: str | None = None,
    league_id: str | None = None,
    stale_after_hours: float = 72.0,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build a scoped snapshot without mutating or refreshing league data."""

    now = now or datetime.now(timezone.utc)
    selector = _resolve_owner_selector(owner_id, owner_display_name)
    player = _detect_player(
        conn,
        player_query=player_query,
        question=question,
    )
    roster_subject_requested = bool(
        question
        and player_query is None
        and player is None
        and should_use_roster_subject(question)
    )
    gaps: list[str] = []
    if selector is None:
        gaps.append(
            "Portfolio owner is not configured. Set FANTASY_PORTFOLIO_OWNER_ID "
            "or FANTASY_PORTFOLIO_OWNER_DISPLAY_NAME."
        )
        roster_rows: list[tuple[Any, ...]] = []
    else:
        roster_rows = _owner_rosters(conn, selector, league_id)
        if not roster_rows:
            gaps.append(f"No rosters matched configured {selector.kind}={selector.value!r}.")

    if (
        (player_query or (question and should_ground_question(question)))
        and player is None
        and not roster_subject_requested
    ):
        gaps.append("No referenced player matched the local players table.")
    if player is not None:
        roster_rows = [
            row
            for row in roster_rows
            if player["player_id"] in {str(value) for value in _loads(row[4], [])}
        ]
        if selector is not None and not roster_rows:
            gaps.append(
                f"{player['full_name']} is not on a roster owned by the configured portfolio owner."
            )

    leagues = [
        _league_context(
            conn,
            row,
            now=now,
            stale_after_hours=stale_after_hours,
        )
        for row in roster_rows
    ]
    for item in leagues:
        if item["ingest"]["status"] != "fresh":
            gaps.append(
                f"{item['league']['name']} ingest is {item['ingest']['status']}."
            )
        if item["data_health"]["status"] not in {"valid"}:
            gaps.append(
                f"{item['league']['name']} stats health is "
                f"{item['data_health']['status']} "
                f"({item['data_health']['integrity_status']})."
            )

    player_context = (
        {**player, **_player_market_context(conn, player["player_id"])}
        if player
        else None
    )
    decision_packets = [
        build_decision_packet(
            conn,
            question=question,
            player=player_context,
            league_context=item,
            subject=_roster_subject(item) if roster_subject_requested else None,
        )
        for item in leagues
        if question and (should_ground_question(question) or roster_subject_requested)
    ]

    return {
        "schema_version": "agent-context/2.0",
        "generated_at": _iso(now.replace(tzinfo=None)),
        "question": question,
        "grounding_recommended": (
            bool(player_query)
            or should_ground_question(question or "")
            or roster_subject_requested
        ),
        "portfolio_owner": (
            {
                "selector": selector.kind,
                "value": selector.value,
                "source": selector.source,
            }
            if selector
            else None
        ),
        "player": player_context,
        "subject": (
            {"subject_type": "roster"}
            if roster_subject_requested
            else {"subject_type": "player"} if player_context else None
        ),
        "leagues": leagues,
        "decision_packets": decision_packets,
        "gaps": gaps,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Emit read-only league context for grounded fantasy decisions."
    )
    request = parser.add_mutually_exclusive_group(required=True)
    request.add_argument("--question", help="Natural-language fantasy question")
    request.add_argument("--player", help="Player name to locate on the portfolio roster")
    parser.add_argument("--owner-id")
    parser.add_argument("--owner-name")
    parser.add_argument("--league-id")
    parser.add_argument("--stale-after-hours", type=float, default=72.0)
    parser.add_argument("--json", action="store_true", help="Emit JSON (default output)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    settings = get_settings()
    db_path = Path(settings.db_path)
    if not db_path.exists():
        print(
            json.dumps(
                {
                    "error": "database_missing",
                    "database_path": str(db_path),
                },
                indent=2,
            )
        )
        return 1

    try:
        conn = duckdb.connect(str(db_path), read_only=True)
        try:
            payload = build_agent_context(
                conn,
                question=args.question,
                player_query=args.player,
                owner_id=args.owner_id,
                owner_display_name=args.owner_name,
                league_id=args.league_id,
                stale_after_hours=args.stale_after_hours,
            )
            payload["database"] = {"path": str(db_path), "mode": "read_only"}
        finally:
            conn.close()

    except (duckdb.Error, ValueError) as exc:
        print(json.dumps({"error": "context_query_failed", "detail": str(exc)}, indent=2))
        return 1

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

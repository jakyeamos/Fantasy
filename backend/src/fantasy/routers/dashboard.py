from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Literal

import duckdb
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from fantasy.config import get_settings
from fantasy.intelligence.constants import REBUILD_DIRECTION_LABELS
from fantasy.routers.deps import get_read_db_conn

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

RECENT_EXPLOIT_WINDOW_DAYS = 14
RECENT_TRADEABILITY_DAYS = 90

SCORECARD_FIELDS = [
    "win_now",
    "future_value",
    "depth",
    "pick_capital",
    "flexibility",
    "fragility",
    "age_risk",
    "liquidity",
    "positional_insulation",
]

SUMMARY_SIGNAL_FIELDS = [
    "pick_capital",
    "win_now",
    "future_value",
    "liquidity",
    "depth",
    "positional_insulation",
]

SUMMARY_SIGNAL_EDGE_LABELS: dict[str, str] = {
    "pick_capital": "Pick capital edge",
    "win_now": "Win-now edge",
    "future_value": "Future value edge",
    "liquidity": "Market liquidity edge",
    "depth": "Depth edge",
    "positional_insulation": "Lineup insulation edge",
}

SUMMARY_SIGNAL_NEUTRAL_LABELS: dict[str, str] = {
    "pick_capital": "Best relative score: pick capital",
    "win_now": "Best relative score: win now",
    "future_value": "Best relative score: future value",
    "liquidity": "Best relative score: market liquidity",
    "depth": "Best relative score: depth",
    "positional_insulation": "Best relative score: lineup insulation",
}

WEAKNESS_LABELS: dict[str, str] = {
    "win_now": "Your lineup needs more weekly production to compete now.",
    "future_value": "Your roster lacks enough insulated long-term value.",
    "depth": "You need more playable depth behind your starters.",
    "pick_capital": "You need more draft capital to unlock flexible moves.",
    "flexibility": "Position mix is skewed toward one position group.",
    "fragility": "You have too many brittle weekly outcomes right now.",
    "age_risk": "Your core is carrying too much age-related downside.",
    "liquidity": "You need more liquid market assets to move when needed.",
    "positional_insulation": "You need more insulation at scarce lineup spots.",
}


class DashboardLeagueSummary(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    league_name: str
    user_roster_id: int | None = None
    direction_label: str
    confidence_band: Literal["High", "Medium", "Low", "--"]
    summary_signal: str
    primary_weakness: str
    top_exploit_window: str | None = None
    last_snapshot_at: str | None = None
    last_ingest_at: str | None = None


class RiserFallerEntry(BaseModel):
    model_config = ConfigDict(frozen=False)

    player_name: str
    delta: float
    reason: str


class ExploitTrigger(BaseModel):
    model_config = ConfigDict(frozen=False)

    type: str
    description: str
    suggested_action: str


class ExploitWindowManager(BaseModel):
    model_config = ConfigDict(frozen=False)

    roster_id: int
    manager_name: str | None = None
    trigger_count: int
    is_high_opportunity: bool
    triggers: list[ExploitTrigger]


class LeagueDetailResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    league_id: str
    league_name: str
    user_roster_id: int | None = None
    direction_label: str
    confidence_band: Literal["High", "Medium", "Low", "--"]
    primary_weakness: str
    risers: list[RiserFallerEntry]
    fallers: list[RiserFallerEntry]
    exploit_windows: list[ExploitWindowManager]
    last_snapshot_at: str | None = None
    last_ingest_at: str | None = None


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _band(confidence: float | None) -> Literal["High", "Medium", "Low", "--"]:
    if confidence is None:
        return "--"
    if confidence >= 0.7:
        return "High"
    if confidence >= 0.4:
        return "Medium"
    return "Low"


def _ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _derive_summary_signal(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    roster_id: int,
    scorecard_row: tuple[Any, ...] | None,
) -> str:
    if scorecard_row is None:
        return "Run Phase 2 intelligence to surface your top edge."

    scorecard = {
        field: float(value)
        for field, value in zip(SCORECARD_FIELDS, scorecard_row, strict=False)
    }

    best_field = SUMMARY_SIGNAL_FIELDS[0]
    best_value = scorecard.get(best_field, 0.0)
    for field in SUMMARY_SIGNAL_FIELDS[1:]:
        value = scorecard.get(field, 0.0)
        if value > best_value:
            best_field = field
            best_value = value

    rows = conn.execute(
        f"""
        SELECT roster_id, {best_field}
        FROM team_scorecards
        WHERE league_id = ?
        ORDER BY {best_field} DESC, roster_id ASC
        """,
        [league_id],
    ).fetchall()
    if not rows:
        return "Run Phase 2 intelligence to surface your top edge."

    rank = next(
        (index for index, (candidate_roster_id, _value) in enumerate(rows, start=1) if int(candidate_roster_id) == roster_id),
        None,
    )
    if rank is None:
        return "Run Phase 2 intelligence to surface your top edge."

    league_size = len(rows)
    edge_cutoff = max(3, (league_size + 3) // 4)
    rank_label = _ordinal(rank)
    if rank <= edge_cutoff:
        label = SUMMARY_SIGNAL_EDGE_LABELS[best_field]
        return f"{label}: {rank_label} of {league_size} in this league."

    label = SUMMARY_SIGNAL_NEUTRAL_LABELS[best_field]
    return f"{label} is {rank_label} of {league_size} in this league."


def _position_group_phrase(position: str, count: int) -> tuple[str, str]:
    labels = {
        "QB": ("QB", "QBs"),
        "RB": ("RB", "RBs"),
        "WR": ("WR", "WRs"),
        "TE": ("TE", "TEs"),
        "K": ("K", "Ks"),
        "DEF": ("DEF", "DEFs"),
        "DL": ("DL", "DLs"),
        "LB": ("LB", "LBs"),
        "DB": ("DB", "DBs"),
        "UNKNOWN": ("Unknown-position player", "Unknown-position players"),
    }
    singular, plural = labels.get(position, (position, f"{position}s"))
    return (singular, "is") if count == 1 else (plural, "are")


def _build_flexibility_note(
    conn: duckdb.DuckDBPyConnection, league_id: str, roster_id: int
) -> str | None:
    roster_row = conn.execute(
        """
        SELECT starters, players, reserve, taxi
        FROM rosters
        WHERE league_id = ? AND roster_id = ?
        LIMIT 1
        """,
        [league_id, roster_id],
    ).fetchone()
    if roster_row is None:
        return None

    starters = [str(player_id) for player_id in _loads(roster_row[0], [])]
    players = [str(player_id) for player_id in _loads(roster_row[1], [])]
    reserve = {str(player_id) for player_id in _loads(roster_row[2], [])}
    taxi = {str(player_id) for player_id in _loads(roster_row[3], [])}
    excluded = set(starters) | reserve | taxi
    roster = starters + [player_id for player_id in players if player_id not in excluded]
    if not roster:
        return None

    position_rows = conn.execute(
        """
        SELECT player_id, COALESCE(position, 'UNKNOWN')
        FROM players
        WHERE player_id IN (SELECT UNNEST(?))
        """,
        [roster],
    ).fetchall()
    player_positions = {str(row[0]): str(row[1] or "UNKNOWN") for row in position_rows}

    counts: dict[str, int] = {}
    for player_id in roster:
        position = player_positions.get(player_id, "UNKNOWN")
        counts[position] = counts.get(position, 0) + 1

    dominant_position, dominant_count = max(
        counts.items(), key=lambda item: (item[1], item[0])
    )
    label, verb = _position_group_phrase(dominant_position, dominant_count)
    share = round((dominant_count / len(roster)) * 100)
    return f"{label} {verb} {dominant_count} of {len(roster)} starters/bench players ({share}%)."


def _derive_primary_weakness(
    scorecard_row: tuple[Any, ...] | None,
    *,
    conn: duckdb.DuckDBPyConnection | None = None,
    league_id: str | None = None,
    roster_id: int | None = None,
) -> str:
    if scorecard_row is None:
        return "Run Phase 2 intelligence to surface the primary roster weakness."
    scorecard = {
        field: float(value)
        for field, value in zip(SCORECARD_FIELDS, scorecard_row, strict=False)
    }
    weakest = min(scorecard.items(), key=lambda item: item[1])[0]
    if (
        weakest == "flexibility"
        and conn is not None
        and league_id is not None
        and roster_id is not None
    ):
        flexibility_note = _build_flexibility_note(conn, league_id, roster_id)
        if flexibility_note is not None:
            return flexibility_note
    return WEAKNESS_LABELS.get(
        weakest, "This roster needs more clarity before surfacing a weakness."
    )


def _portfolio_owner_selection(
    conn: duckdb.DuckDBPyConnection,
) -> tuple[str | None, bool]:
    settings = get_settings()

    if settings.PORTFOLIO_OWNER_ID:
        row = conn.execute(
            """
            SELECT owner_id
            FROM rosters
            WHERE owner_id = ?
            LIMIT 1
            """,
            [settings.PORTFOLIO_OWNER_ID],
        ).fetchone()
        return (str(row[0]), False) if row else (None, False)

    if settings.PORTFOLIO_OWNER_DISPLAY_NAME:
        row = conn.execute(
            """
            SELECT owner_id, COUNT(DISTINCT league_id) AS league_count
            FROM rosters
            WHERE owner_id IS NOT NULL
              AND owner_display_name IS NOT NULL
              AND lower(owner_display_name) = lower(?)
            GROUP BY owner_id
            ORDER BY league_count DESC, owner_id ASC
            LIMIT 1
            """,
            [settings.PORTFOLIO_OWNER_DISPLAY_NAME],
        ).fetchone()
        return (str(row[0]), False) if row else (None, False)

    row = conn.execute(
        """
        SELECT owner_id, COUNT(DISTINCT league_id) AS league_count
        FROM rosters
        WHERE owner_id IS NOT NULL
        GROUP BY owner_id
        ORDER BY league_count DESC, owner_id ASC
        LIMIT 1
        """
    ).fetchone()
    return (str(row[0]), True) if row else (None, True)


def _user_roster_for_league(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    portfolio_owner_id: str | None,
    *,
    allow_fallback: bool,
) -> tuple[int | None, str | None]:
    if portfolio_owner_id is not None:
        owner_row = conn.execute(
            """
            SELECT roster_id, owner_id
            FROM rosters
            WHERE league_id = ? AND owner_id = ?
            ORDER BY roster_id
            LIMIT 1
            """,
            [league_id, portfolio_owner_id],
        ).fetchone()
        if owner_row is not None:
            return int(owner_row[0]), owner_row[1]

    if not allow_fallback:
        return None, None

    fallback = conn.execute(
        """
        SELECT roster_id, owner_id
        FROM rosters
        WHERE league_id = ?
        ORDER BY roster_id
        LIMIT 1
        """,
        [league_id],
    ).fetchone()
    if fallback is None:
        return None, None
    return int(fallback[0]), fallback[1]


def _latest_snapshot_at(conn: duckdb.DuckDBPyConnection, league_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT CAST(MAX(snapshot_at) AS VARCHAR)
        FROM league_snapshots
        WHERE league_id = ?
        """,
        [league_id],
    ).fetchone()
    return str(row[0]) if row and row[0] is not None else None


def _latest_ingest_at(conn: duckdb.DuckDBPyConnection, league_id: str) -> str | None:
    row = conn.execute(
        """
        SELECT CAST(MAX(completed_at) AS VARCHAR)
        FROM ingest_runs
        WHERE league_id = ? AND status = 'complete'
        """,
        [league_id],
    ).fetchone()
    return str(row[0]) if row and row[0] is not None else None


def _recent_cutoff(days: int) -> datetime:
    return datetime.now() - timedelta(days=days)


def _tradeable_rosters(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    user_roster_id: int | None,
    *,
    days: int,
) -> set[int]:
    rows = conn.execute(
        """
        SELECT roster_ids
        FROM transactions
        WHERE league_id = ? AND type = 'trade' AND status = 'complete' AND created_at >= ?
        """,
        [league_id, _recent_cutoff(days)],
    ).fetchall()
    roster_ids: set[int] = set()
    for row in rows:
        for value in _loads(row[0], []):
            roster_id = int(value)
            if user_roster_id is not None and roster_id == user_roster_id:
                continue
            roster_ids.add(roster_id)
    return roster_ids


def _build_exploit_windows(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    user_roster_id: int | None,
) -> list[ExploitWindowManager]:
    roster_rows = conn.execute(
        """
        SELECT roster_id, owner_id, owner_display_name
        FROM rosters
        WHERE league_id = ?
        ORDER BY roster_id
        """,
        [league_id],
    ).fetchall()
    owner_names = {
        int(row[0]): str(row[2] or row[1] or f"Roster {int(row[0])}") for row in roster_rows
    }
    direction_map = {
        int(row[0]): str(row[1])
        for row in conn.execute(
            """
            SELECT roster_id, primary_label
            FROM team_directions
            WHERE league_id = ?
            """,
            [league_id],
        ).fetchall()
    }
    player_positions = {
        str(row[0]): str(row[1] or "UNKNOWN")
        for row in conn.execute(
            "SELECT player_id, position FROM players"
        ).fetchall()
    }

    transaction_rows = conn.execute(
        """
        SELECT roster_ids, adds, drops, draft_picks
        FROM transactions
        WHERE league_id = ? AND type = 'trade' AND status = 'complete' AND created_at >= ?
        ORDER BY created_at DESC NULLS LAST
        """,
        [league_id, _recent_cutoff(RECENT_EXPLOIT_WINDOW_DAYS)],
    ).fetchall()
    trade_counts: dict[int, int] = {}
    pick_counts: dict[int, int] = {}
    position_receipts: dict[int, dict[str, int]] = {}
    for row in transaction_rows:
        roster_ids = [int(value) for value in _loads(row[0], [])]
        adds = _loads(row[1], {})
        picks = _loads(row[3], [])
        for roster_id in roster_ids:
            if user_roster_id is not None and roster_id == user_roster_id:
                continue
            trade_counts[roster_id] = trade_counts.get(roster_id, 0) + 1
            position_receipts.setdefault(roster_id, {})
        for player_id, target_roster in adds.items():
            roster_id = int(target_roster)
            if user_roster_id is not None and roster_id == user_roster_id:
                continue
            position = player_positions.get(str(player_id), "UNKNOWN")
            bucket = position_receipts.setdefault(roster_id, {})
            bucket[position] = bucket.get(position, 0) + 1
        for pick in picks:
            owner_id = pick.get("owner_id")
            previous_owner_id = pick.get("previous_owner_id")
            for raw_roster in (owner_id, previous_owner_id):
                if raw_roster is None:
                    continue
                roster_id = int(raw_roster)
                if user_roster_id is not None and roster_id == user_roster_id:
                    continue
                pick_counts[roster_id] = pick_counts.get(roster_id, 0) + 1

    windows: list[ExploitWindowManager] = []
    roster_ids = sorted(set(owner_names) | set(trade_counts) | set(pick_counts))
    for roster_id in roster_ids:
        if user_roster_id is not None and roster_id == user_roster_id:
            continue
        triggers: list[ExploitTrigger] = []
        trade_count = trade_counts.get(roster_id, 0)
        if trade_count >= 2:
            triggers.append(
                ExploitTrigger(
                    type="recent_activity",
                    description=f"{trade_count} recent trades suggest this manager is open to deals.",
                    suggested_action="Lead with a concise offer while the manager is actively moving pieces.",
                )
            )
        pick_count = pick_counts.get(roster_id, 0)
        if pick_count >= 1:
            triggers.append(
                ExploitTrigger(
                    type="pick_activity",
                    description=(
                        f"{pick_count} recent pick swaps suggest this manager is willing "
                        "to rebalance future assets."
                    ),
                    suggested_action="Test veteran-for-pick or pick-for-insulation frameworks first.",
                )
            )
        position_counts = position_receipts.get(roster_id, {})
        if position_counts:
            chased_position, chase_count = max(
                position_counts.items(), key=lambda item: item[1]
            )
            if chased_position != "UNKNOWN" and chase_count >= 2:
                triggers.append(
                    ExploitTrigger(
                        type="position_chase",
                        description=f"They have repeatedly added {chased_position} assets in recent deals.",
                        suggested_action=f"Offer {chased_position} depth at a premium while demand is visible.",
                    )
                )
        direction_label = direction_map.get(roster_id)
        if (
            direction_label in REBUILD_DIRECTION_LABELS
            and trade_count >= 2
            and pick_counts.get(roster_id, 0) == 0
        ):
            triggers.append(
                ExploitTrigger(
                    type="direction_noise",
                    description=f"Recent trade volume does not appear to reinforce a {direction_label.replace('_', ' ')} path.",
                    suggested_action="Float flexible two-for-one offers that simplify their roster decisions.",
                )
            )

        if not triggers:
            continue
        windows.append(
            ExploitWindowManager(
                roster_id=roster_id,
                manager_name=owner_names.get(roster_id),
                trigger_count=len(triggers),
                is_high_opportunity=trade_count >= 7
                or (
                    len(triggers) >= 3
                    and trade_count >= 5
                    and pick_count >= 10
                ),
                triggers=triggers,
            )
        )

    return sorted(
        windows,
        key=lambda window: (window.trigger_count, window.is_high_opportunity, window.roster_id),
        reverse=True,
    )


def _top_exploit_window(
    conn: duckdb.DuckDBPyConnection, league_id: str, user_roster_id: int | None
) -> str | None:
    windows = _build_exploit_windows(conn, league_id, user_roster_id)
    if not windows:
        return None
    top = windows[0]
    manager_name = top.manager_name or f"Roster {top.roster_id}"
    return f"{manager_name}: {top.trigger_count} live triggers"


def _snapshot_pair_payloads(
    conn: duckdb.DuckDBPyConnection, league_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT payload_json
        FROM league_snapshots
        WHERE league_id = ?
        ORDER BY snapshot_at DESC, id DESC
        LIMIT 2
        """,
        [league_id],
    ).fetchall()
    payloads = [_loads(row[0], {}) for row in rows]
    latest = payloads[0] if payloads else {}
    previous = payloads[1] if len(payloads) > 1 else {}
    return latest, previous


def _build_risers_fallers(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    user_roster_id: int | None,
) -> tuple[list[RiserFallerEntry], list[RiserFallerEntry]]:
    latest_payload, previous_payload = _snapshot_pair_payloads(conn, league_id)
    latest_state = latest_payload.get("state", {}) if isinstance(latest_payload, dict) else {}
    previous_state = previous_payload.get("state", {}) if isinstance(previous_payload, dict) else {}
    if not latest_state or not previous_state:
        return [], []

    actionable_rosters = {
        roster_id
        for roster_id in _tradeable_rosters(
            conn,
            league_id,
            user_roster_id,
            days=RECENT_TRADEABILITY_DAYS,
        )
    }
    previous_market: dict[tuple[int, str], float] = {}
    for roster in previous_state.get("rosters", []):
        roster_id = int(roster.get("roster_id", 0))
        for player in roster.get("player_values", []):
            lens_market = player.get("lens_market")
            if lens_market is None:
                continue
            previous_market[(roster_id, str(player.get("player_id")))] = float(lens_market)

    deltas: list[tuple[str, float]] = []
    for roster in latest_state.get("rosters", []):
        roster_id = int(roster.get("roster_id", 0))
        if user_roster_id is not None and roster_id == user_roster_id:
            continue
        if roster_id not in actionable_rosters:
            continue
        for player in roster.get("player_values", []):
            player_id = str(player.get("player_id"))
            current_value = player.get("lens_market")
            previous_value = previous_market.get((roster_id, player_id))
            if current_value is None or previous_value is None:
                continue
            delta = round(float(current_value) - previous_value, 2)
            if abs(delta) < 0.01:
                continue
            deltas.append((str(player.get("player_name") or player_id), delta))

    risers = [
        RiserFallerEntry(
            player_name=name,
            delta=delta,
            reason="Market value rose versus the previous ingest snapshot.",
        )
        for name, delta in sorted(deltas, key=lambda item: item[1], reverse=True)[:5]
        if delta > 0
    ]
    fallers = [
        RiserFallerEntry(
            player_name=name,
            delta=delta,
            reason="Market value fell versus the previous ingest snapshot.",
        )
        for name, delta in sorted(deltas, key=lambda item: item[1])[:5]
        if delta < 0
    ]
    return risers, fallers


@router.get("/summary", response_model=list[DashboardLeagueSummary])
def get_dashboard_summary(
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> list[DashboardLeagueSummary]:
    leagues = conn.execute(
        "SELECT league_id, name FROM leagues ORDER BY name, league_id"
    ).fetchall()
    portfolio_owner, allow_fallback = _portfolio_owner_selection(conn)
    summaries: list[DashboardLeagueSummary] = []
    for league_id, league_name in leagues:
        roster_id, _ = _user_roster_for_league(
            conn,
            str(league_id),
            portfolio_owner,
            allow_fallback=allow_fallback,
        )
        direction_label = "Analysis not yet run"
        confidence_band: Literal["High", "Medium", "Low", "--"] = "--"
        summary_signal = "Run Phase 2 intelligence to surface your top edge."
        primary_weakness = "Run Phase 2 intelligence to surface the primary roster weakness."
        if roster_id is not None:
            direction_row = conn.execute(
                """
                SELECT primary_label, confidence
                FROM team_directions
                WHERE league_id = ? AND roster_id = ?
                """,
                [league_id, roster_id],
            ).fetchone()
            if direction_row is not None:
                direction_label = str(direction_row[0])
                confidence_band = _band(float(direction_row[1]))
            scorecard_row = conn.execute(
                """
                SELECT win_now, future_value, depth, pick_capital, flexibility,
                       fragility, age_risk, liquidity, positional_insulation
                FROM team_scorecards
                WHERE league_id = ? AND roster_id = ?
                """,
                [league_id, roster_id],
            ).fetchone()
            summary_signal = _derive_summary_signal(
                conn,
                str(league_id),
                roster_id,
                scorecard_row,
            )
            primary_weakness = _derive_primary_weakness(
                scorecard_row,
                conn=conn,
                league_id=str(league_id),
                roster_id=roster_id,
            )

        summaries.append(
            DashboardLeagueSummary(
                league_id=str(league_id),
                league_name=str(league_name),
                user_roster_id=roster_id,
                direction_label=direction_label,
                confidence_band=confidence_band,
                summary_signal=summary_signal,
                primary_weakness=primary_weakness,
                top_exploit_window=_top_exploit_window(conn, str(league_id), roster_id),
                last_snapshot_at=_latest_snapshot_at(conn, str(league_id)),
                last_ingest_at=_latest_ingest_at(conn, str(league_id)),
            )
        )
    return summaries


@router.get("/league/{league_id}", response_model=LeagueDetailResponse)
def get_league_detail(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
) -> LeagueDetailResponse:
    league_row = conn.execute(
        "SELECT name FROM leagues WHERE league_id = ?",
        [league_id],
    ).fetchone()
    if league_row is None:
        raise HTTPException(status_code=404, detail="League not found")

    portfolio_owner, allow_fallback = _portfolio_owner_selection(conn)
    roster_id, _ = _user_roster_for_league(
        conn,
        league_id,
        portfolio_owner,
        allow_fallback=allow_fallback,
    )
    direction_label = "Analysis not yet run"
    confidence_band: Literal["High", "Medium", "Low", "--"] = "--"
    primary_weakness = "Run Phase 2 intelligence to surface the primary roster weakness."

    if roster_id is not None:
        direction_row = conn.execute(
            """
            SELECT primary_label, confidence
            FROM team_directions
            WHERE league_id = ? AND roster_id = ?
            """,
            [league_id, roster_id],
        ).fetchone()
        if direction_row is not None:
            direction_label = str(direction_row[0])
            confidence_band = _band(float(direction_row[1]))
        scorecard_row = conn.execute(
            """
            SELECT win_now, future_value, depth, pick_capital, flexibility,
                   fragility, age_risk, liquidity, positional_insulation
            FROM team_scorecards
            WHERE league_id = ? AND roster_id = ?
            """,
            [league_id, roster_id],
        ).fetchone()
        primary_weakness = _derive_primary_weakness(
            scorecard_row,
            conn=conn,
            league_id=league_id,
            roster_id=roster_id,
        )

    risers, fallers = _build_risers_fallers(conn, league_id, roster_id)
    exploit_windows = _build_exploit_windows(conn, league_id, roster_id)
    return LeagueDetailResponse(
        league_id=league_id,
        league_name=str(league_row[0]),
        user_roster_id=roster_id,
        direction_label=direction_label,
        confidence_band=confidence_band,
        primary_weakness=primary_weakness,
        risers=risers,
        fallers=fallers,
        exploit_windows=exploit_windows,
        last_snapshot_at=_latest_snapshot_at(conn, league_id),
        last_ingest_at=_latest_ingest_at(conn, league_id),
    )

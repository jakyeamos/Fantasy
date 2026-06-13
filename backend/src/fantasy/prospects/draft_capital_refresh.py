from __future__ import annotations

import html
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

import duckdb
import httpx
import polars as pl

from fantasy.context.context_repo import ContextRepo
from fantasy.context.freshness_service import FreshnessService
from fantasy.prospects.nflreadpy_loader import NflReadPyLoader
from fantasy.rookie.rookie_engine import RookieEngine

FANTASY_POSITIONS = {"QB", "RB", "WR", "TE"}
NBC_DRAFT_TRACKER_URL = (
    "https://www.nbcsports.com/nfl/profootballtalk/news/"
    "{draft_year}-nfl-draft-picks-full-tracker-of-every-selection-rounds-1-7"
)


@dataclass(frozen=True)
class ActualDraftPick:
    player_name: str
    position: str
    pick: int
    team: str | None = None
    college: str | None = None
    source: str = "unknown"


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _safe_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _strip_html(raw_html: str) -> str:
    text = re.sub(r"<(script|style).*?</\1>", " ", raw_html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\n{2,}", "\n", text)


def _parse_nbc_tracker(text: str, draft_year: int) -> list[ActualDraftPick]:
    picks: list[ActualDraftPick] = []
    current_round: int | None = None
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        round_match = re.fullmatch(r"Round\s+(\d+)", line, flags=re.IGNORECASE)
        if round_match:
            current_round = int(round_match.group(1))
            continue
        pick_match = re.match(
            r"^(?P<pick>\d{1,3})\s+(?P<team>.+?):\s+"
            r"(?P<name>[A-Za-z.'\- ]+),\s+(?P<position>[A-Z/]+),\s+(?P<college>.+)$",
            line,
        )
        if pick_match is None:
            continue
        position = pick_match.group("position").split("/")[0]
        if position not in FANTASY_POSITIONS:
            continue
        pick = int(pick_match.group("pick"))
        if current_round is None:
            current_round = ((pick - 1) // 32) + 1
        picks.append(
            ActualDraftPick(
                player_name=pick_match.group("name").strip(),
                position=position,
                pick=pick,
                team=pick_match.group("team").strip(),
                college=pick_match.group("college").strip(),
                source=f"nbc_tracker_{draft_year}",
            )
        )
    return picks


def fetch_nbc_draft_picks(draft_year: int) -> list[ActualDraftPick]:
    response = httpx.get(NBC_DRAFT_TRACKER_URL.format(draft_year=draft_year), timeout=30.0)
    response.raise_for_status()
    return _parse_nbc_tracker(_strip_html(response.text), draft_year)


def load_nflverse_draft_picks(draft_year: int) -> list[ActualDraftPick]:
    df = NflReadPyLoader().load_draft_picks(draft_year, draft_year + 1)
    if df.is_empty():
        return []
    if "season" in df.columns:
        df = df.filter(pl.col("season") == draft_year)
    picks: list[ActualDraftPick] = []
    for row in df.to_dicts():
        position = _safe_str(row.get("position"))
        pick = _safe_int(row.get("pick") or row.get("overall_pick") or row.get("draft_pick"))
        player_name = _safe_str(row.get("pfr_player_name") or row.get("player_name") or row.get("name"))
        if position not in FANTASY_POSITIONS or pick is None or player_name is None:
            continue
        picks.append(
            ActualDraftPick(
                player_name=player_name,
                position=position,
                pick=pick,
                team=_safe_str(row.get("team")),
                college=_safe_str(row.get("college")),
                source="nflverse_draft_picks",
            )
        )
    return picks


def fetch_actual_draft_picks(draft_year: int) -> list[ActualDraftPick]:
    picks = load_nflverse_draft_picks(draft_year)
    if picks:
        return picks
    return fetch_nbc_draft_picks(draft_year)


def refresh_actual_draft_capital(
    conn: duckdb.DuckDBPyConnection,
    *,
    draft_year: int,
    picks: list[ActualDraftPick] | None = None,
    rebuild_boards: bool = True,
) -> dict[str, Any]:
    actual_picks = picks if picks is not None else fetch_actual_draft_picks(draft_year)
    if not actual_picks:
        return {
            "draft_year": draft_year,
            "source_rows": 0,
            "matched_rows": 0,
            "updated_rows": 0,
            "unmatched_rows": 0,
            "rebuilt_boards": 0,
        }

    feature_rows = conn.execute(
        """
        SELECT player_id, player_name, position, draft_ovr
        FROM historical_prospect_features
        WHERE draft_year = ?
          AND position IN ('QB', 'RB', 'WR', 'TE')
        """,
        [draft_year],
    ).fetchall()
    by_exact = {
        (str(row[2]), _normalize_name(str(row[1]))): row
        for row in feature_rows
    }
    by_position: dict[str, list[tuple[str, str, str, int | None]]] = {}
    for row in feature_rows:
        by_position.setdefault(str(row[2]), []).append(
            (str(row[0]), str(row[1]), str(row[2]), _safe_int(row[3]))
        )

    matched_rows = 0
    updated_rows = 0
    for pick in actual_picks:
        matched = by_exact.get((pick.position, _normalize_name(pick.player_name)))
        if matched is None:
            matched = _fuzzy_match_pick(pick, by_position.get(pick.position, []))
        if matched is None:
            continue
        matched_rows += 1
        player_id = str(matched[0])
        previous_pick = _safe_int(matched[3])
        if previous_pick == pick.pick:
            continue
        conn.execute(
            """
            UPDATE historical_prospect_features
            SET draft_ovr = ?,
                adp = CASE WHEN adp IS NULL THEN ? ELSE adp END
            WHERE player_id = ?
              AND draft_year = ?
            """,
            [pick.pick, float(pick.pick), player_id, draft_year],
        )
        updated_rows += 1

    league_ids = [
        str(row[0])
        for row in conn.execute(
            """
            SELECT league_id
            FROM leagues
            ORDER BY league_id
            """
        ).fetchall()
    ]
    rebuilt_boards = 0
    if rebuild_boards:
        engine = RookieEngine(conn)
        for league_id in league_ids:
            engine.compute_board(league_id)
            try:
                freshness = FreshnessService(repo=ContextRepo(conn))
                for domain in ("draft_capital", "landing_spots"):
                    freshness.mark_refreshed(
                        league_id,
                        domain,
                        notes=f"Updated actual NFL Draft capital for {draft_year}.",
                    )
            except duckdb.Error:
                pass
            rebuilt_boards += 1

    return {
        "draft_year": draft_year,
        "source_rows": len(actual_picks),
        "matched_rows": matched_rows,
        "updated_rows": updated_rows,
        "unmatched_rows": len(actual_picks) - matched_rows,
        "rebuilt_boards": rebuilt_boards,
    }


def _fuzzy_match_pick(
    pick: ActualDraftPick,
    candidates: list[tuple[str, str, str, int | None]],
) -> tuple[str, str, str, int | None] | None:
    normalized_pick_name = _normalize_name(pick.player_name)
    best_candidate: tuple[str, str, str, int | None] | None = None
    best_ratio = 0.0
    for candidate in candidates:
        ratio = SequenceMatcher(None, normalized_pick_name, _normalize_name(candidate[1])).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_candidate = candidate
    if best_candidate is not None and best_ratio >= 0.92:
        return best_candidate
    surname = _normalize_name(pick.player_name.split()[-1])
    surname_matches = [
        candidate
        for candidate in candidates
        if _normalize_name(candidate[1].split()[-1]) == surname
    ]
    if len(surname_matches) == 1:
        return surname_matches[0]
    return None


__all__ = [
    "ActualDraftPick",
    "fetch_actual_draft_picks",
    "refresh_actual_draft_capital",
]

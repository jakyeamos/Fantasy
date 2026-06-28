from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from statistics import median
from typing import Any, Literal

import duckdb

from fantasy.recommendation.card_engine import RecommendationCardEngine
from fantasy.waiver.constants import (
    DIRECTION_URGENCY,
    FAAB_CEILING_PCT,
    FAAB_FLOOR_PCT,
    FAAB_HIGH_MULT,
    FAAB_LOW_MULT,
    FAAB_MAX_PCT_OF_REMAINING,
    FAAB_SCARCITY_ADJ_MAX,
    FAAB_START_PENALTY,
    FAAB_URGENCY_ADJ_MAX,
    FREE_AGENT_VALUE_FLOOR,
    STALE_INGEST_HOURS,
    WAIVER_TYPE_LABELS,
)
from fantasy.waiver.models import WaiverRecommendation, WaiverRecommendationsResponse


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _parse_timestamp(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _format_direction(direction_label: str) -> str:
    return direction_label.replace("_", " ")


def compute_bid_range(
    player_value_score: float,
    remaining_faab: int,
    league_median_remaining: int,
    direction_urgency: float,
    positional_scarcity: float,
    is_immediate_start: bool,
) -> tuple[int, int, int]:
    if remaining_faab <= 0 or player_value_score < FREE_AGENT_VALUE_FLOOR:
        return (0, 0, 0)
    _ = league_median_remaining
    base_pct = player_value_score / 100.0 * FAAB_MAX_PCT_OF_REMAINING
    scarcity_adj = positional_scarcity / 100.0 * FAAB_SCARCITY_ADJ_MAX
    urgency_adj = direction_urgency * FAAB_URGENCY_ADJ_MAX
    start_adj = 0.0 if is_immediate_start else -FAAB_START_PENALTY
    mid_pct = _clamp(
        base_pct + scarcity_adj + urgency_adj + start_adj,
        FAAB_FLOOR_PCT,
        FAAB_CEILING_PCT,
    )
    mid = int(remaining_faab * mid_pct)
    if mid <= 0:
        return (0, 0, 0)
    low = max(1, int(mid * FAAB_LOW_MULT))
    high = min(remaining_faab, int(mid * FAAB_HIGH_MULT))
    return low, mid, high


def get_available_players(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
) -> list[str]:
    rostered_ids: set[str] = set()
    for row in conn.execute(
        """
        SELECT players
        FROM rosters
        WHERE league_id = ?
        """,
        [league_id],
    ).fetchall():
        rostered_ids.update(
            str(player_id)
            for player_id in _loads(row[0], [])
            if player_id not in (None, "", 0, "0")
        )

    rows = conn.execute(
        """
        SELECT player_id, metadata_blob
        FROM players
        """
    ).fetchall()
    allowed_statuses = {"Active", "Injured Reserve", ""}
    available_ids: list[str] = []
    for player_id, metadata_blob in rows:
        metadata = _loads(metadata_blob, {})
        status = str(metadata.get("status") or "")
        if str(player_id) in rostered_ids:
            continue
        if status not in allowed_statuses:
            continue
        available_ids.append(str(player_id))
    return available_ids


def get_faab_state(
    conn: duckdb.DuckDBPyConnection,
    league_id: str,
    roster_id: int,
) -> dict[str, Any]:
    league_row = conn.execute(
        """
        SELECT settings_blob, CAST(ingested_at AS VARCHAR)
        FROM leagues
        WHERE league_id = ?
        LIMIT 1
        """,
        [league_id],
    ).fetchone()
    roster_row = conn.execute(
        """
        SELECT waiver_budget_used, waiver_position, CAST(ingested_at AS VARCHAR)
        FROM rosters
        WHERE league_id = ? AND roster_id = ?
        LIMIT 1
        """,
        [league_id, roster_id],
    ).fetchone()

    settings = _loads(league_row[0], {}) if league_row else {}
    total_budget = (
        int(settings.get("waiver_budget") or 100)
        if settings.get("waiver_budget") is not None
        else 100
    )
    waiver_type_raw = int(settings.get("waiver_type", 0) or 0)
    waiver_budget_used = int(roster_row[0] or 0) if roster_row else 0
    waiver_position = int(roster_row[1]) if roster_row and roster_row[1] is not None else None
    remaining_faab = max(0, total_budget - waiver_budget_used)

    timestamps = [
        _parse_timestamp(str(league_row[1])) if league_row and league_row[1] is not None else None,
        _parse_timestamp(str(roster_row[2])) if roster_row and roster_row[2] is not None else None,
    ]
    valid_timestamps = [ts for ts in timestamps if ts is not None]
    hours_since_ingest: float | None = None
    if valid_timestamps:
        latest = max(valid_timestamps)
        latest_utc = latest if latest.tzinfo is not None else latest.replace(tzinfo=timezone.utc)
        hours_since_ingest = (datetime.now(timezone.utc) - latest_utc).total_seconds() / 3600

    return {
        "total_budget": total_budget,
        "waiver_budget_used": waiver_budget_used,
        "waiver_position": waiver_position,
        "remaining_faab": remaining_faab,
        "waiver_type_raw": waiver_type_raw,
        "waiver_type_label": WAIVER_TYPE_LABELS.get(waiver_type_raw, "unknown"),
        "hours_since_ingest": hours_since_ingest,
        "data_freshness_warning": (
            hours_since_ingest is not None and hours_since_ingest > STALE_INGEST_HOURS
        ),
    }


class WaiverEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn
        self._card_engine = RecommendationCardEngine(conn)

    def _league_median_remaining(self, league_id: str, total_budget: int) -> int:
        rows = self._conn.execute(
            """
            SELECT waiver_budget_used
            FROM rosters
            WHERE league_id = ?
            """,
            [league_id],
        ).fetchall()
        if not rows:
            return total_budget
        remaining = [max(0, total_budget - int(row[0] or 0)) for row in rows]
        return int(median(remaining))

    def _direction_label(self, league_id: str, roster_id: int) -> str:
        row = self._conn.execute(
            """
            SELECT primary_label
            FROM team_directions
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        return str(row[0]) if row and row[0] else "fringe_playoff"

    def _roster_needs(
        self,
        league_id: str,
        roster_id: int,
    ) -> tuple[set[str], Counter[str], Counter[str]]:
        roster_row = self._conn.execute(
            """
            SELECT players
            FROM rosters
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        league_row = self._conn.execute(
            """
            SELECT roster_positions
            FROM leagues
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        player_ids = [str(player_id) for player_id in _loads(roster_row[0], [])] if roster_row else []
        if not player_ids:
            return set(), Counter(), Counter()

        player_rows = self._conn.execute(
            """
            SELECT player_id, position
            FROM players
            WHERE player_id IN (SELECT UNNEST(?))
            """,
            [player_ids],
        ).fetchall()
        roster_counts: Counter[str] = Counter(str(row[1] or "") for row in player_rows if row[1])
        starter_requirements = Counter(
            str(position)
            for position in _loads(league_row[0], [])
            if str(position) in {"QB", "RB", "WR", "TE"}
        ) if league_row else Counter()
        weak_positions = {
            position
            for position, needed in starter_requirements.items()
            if roster_counts.get(position, 0) < needed + 1
        }
        return weak_positions, starter_requirements, roster_counts

    def _position_limits(self, league_id: str) -> dict[str, int]:
        league_row = self._conn.execute(
            """
            SELECT settings_blob
            FROM leagues
            WHERE league_id = ?
            LIMIT 1
            """,
            [league_id],
        ).fetchone()
        settings = _loads(league_row[0], {}) if league_row else {}
        limits: dict[str, int] = {}
        for position in ("QB", "RB", "WR", "TE"):
            raw_limit = settings.get(f"position_limit_{position.lower()}")
            if raw_limit is None:
                continue
            try:
                limit = int(raw_limit)
            except (TypeError, ValueError):
                continue
            if limit > 0:
                limits[position] = limit
        return limits

    def _stats_map(self, player_ids: list[str]) -> dict[str, float]:
        if not player_ids:
            return {}
        rows = self._conn.execute(
            """
            SELECT player_id, AVG(fantasy_points) AS avg_points
            FROM player_stats_weekly
            WHERE player_id IN (SELECT UNNEST(?))
            GROUP BY player_id
            """,
            [player_ids],
        ).fetchall()
        return {str(row[0]): float(row[1]) for row in rows if row[1] is not None}

    def _adp_map(self, player_ids: list[str]) -> dict[str, float]:
        if not player_ids:
            return {}
        rows = self._conn.execute(
            """
            SELECT player_id, adp
            FROM player_adp_baseline
            WHERE player_id IN (SELECT UNNEST(?))
            """,
            [player_ids],
        ).fetchall()
        return {str(row[0]): float(row[1]) for row in rows if row[1] is not None}

    def _player_rows(self, player_ids: list[str]) -> list[dict[str, Any]]:
        if not player_ids:
            return []
        rows = self._conn.execute(
            """
            SELECT player_id, full_name, position, team, age
            FROM players
            WHERE player_id IN (SELECT UNNEST(?))
            """,
            [player_ids],
        ).fetchall()
        return [
            {
                "player_id": str(row[0]),
                "player_name": str(row[1] or row[0]),
                "position": str(row[2] or "FLEX"),
                "team": str(row[3]) if row[3] is not None else None,
                "age": int(row[4]) if row[4] is not None else None,
            }
            for row in rows
        ]

    def _drop_candidates(
        self,
        league_id: str,
        roster_id: int,
    ) -> list[dict[str, str]]:
        roster_row = self._conn.execute(
            """
            SELECT players, starters, reserve, taxi
            FROM rosters
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if roster_row is None:
            return []

        roster_ids = [str(player_id) for player_id in _loads(roster_row[0], [])]
        starters = {str(player_id) for player_id in _loads(roster_row[1], [])}
        protected = starters | {str(player_id) for player_id in _loads(roster_row[2], [])}
        protected |= {str(player_id) for player_id in _loads(roster_row[3], [])}
        bench_ids = [
            player_id
            for player_id in roster_ids
            if player_id not in protected and player_id not in (None, "", "0")
        ]
        if not bench_ids:
            return []

        player_rows = self._player_rows(bench_ids)
        stats_map = self._stats_map(bench_ids)
        adp_map = self._adp_map(bench_ids)
        scored: list[tuple[float, dict[str, str]]] = []
        for player in player_rows:
            player_id = str(player["player_id"])
            avg_points = stats_map.get(player_id)
            adp = adp_map.get(player_id)
            score = 35.0
            if avg_points is not None:
                score += min(35.0, avg_points * 4.0)
            if adp is not None:
                score += max(0.0, 45.0 - min(45.0, adp / 4.0))
            age = player.get("age")
            if age is not None and int(age) >= 29:
                score -= 8.0
            reason_parts = ["lowest bench asset by production and market proxy"]
            if avg_points is not None:
                reason_parts.append(f"{avg_points:.1f} weekly points")
            if adp is not None:
                reason_parts.append(f"ADP {adp:.0f}")
            scored.append(
                (
                    score,
                    {
                        "player_id": player_id,
                        "player_name": str(player["player_name"]),
                        "position": str(player["position"]),
                        "reason": "; ".join(reason_parts),
                    },
                )
            )
        scored.sort(key=lambda item: (item[0], item[1]["player_name"].lower()))
        return [payload for _, payload in scored[:5]]

    def _score_available_player(
        self,
        player: dict[str, Any],
        *,
        weak_positions: set[str],
        starter_requirements: Counter[str],
        direction_label: str,
        avg_points: float | None,
        adp: float | None,
    ) -> tuple[float, float, bool]:
        position = str(player["position"])
        age = player.get("age")
        immediate_start = position in weak_positions and (
            (avg_points is not None and avg_points >= 6.0)
            or starter_requirements.get(position, 0) > 0
        )
        base_by_position = {
            "QB": 20.0,
            "RB": 28.0,
            "WR": 26.0,
            "TE": 18.0,
        }
        score = base_by_position.get(position, 18.0)
        if avg_points is not None:
            score = max(score, min(100.0, avg_points * 6.0))
        if adp is not None:
            score = max(score, max(10.0, 72.0 - adp))
        if age is not None:
            if age <= 24:
                score += 8.0
            elif age <= 27:
                score += 4.0
            elif age >= 30:
                score -= 8.0
        if immediate_start:
            score += 6.0
        if direction_label in {"hard_rebuild", "soft_rebuild", "elite_value_accumulation", "one_year_punt"}:
            if age is not None and age <= 25:
                score += 4.0
            elif age is not None and age >= 29:
                score -= 6.0
        if direction_label in {"true_contender", "fragile_contender"} and avg_points is not None:
            score += min(6.0, avg_points / 2.0)
        score = _clamp(score, 0.0, 100.0)
        scarcity = 70.0 if position in weak_positions else 45.0 if starter_requirements.get(position, 0) else 25.0
        return score, scarcity, immediate_start

    def _urgency_label(
        self,
        recommendation_label: str,
        bid_mid: int | None,
        remaining_faab: int | None,
        player_score: float,
    ) -> str:
        if recommendation_label == "rolling_waiver":
            return "High" if player_score >= 65 else "Medium" if player_score >= 40 else "Low"
        if remaining_faab is None or remaining_faab <= 0 or bid_mid is None:
            return "Low"
        pct = bid_mid / max(1, remaining_faab)
        if pct > 0.15:
            return "High"
        if pct >= 0.05:
            return "Medium"
        return "Low"

    def _roster_fit_label(
        self,
        *,
        position: str,
        weak_positions: set[str],
        is_immediate_start: bool,
        age: int | None,
    ) -> str:
        if is_immediate_start:
            return f"Starter patch at {position}"
        if position in weak_positions:
            return f"Depth need at {position}"
        if age is not None and age <= 25:
            return "Dynasty stash"
        return "Bench churn upgrade"

    def _confidence_label(
        self,
        *,
        player_score: float,
        data_freshness_warning: bool,
    ) -> Literal["HIGH", "MEDIUM", "LOW"]:
        if data_freshness_warning and player_score < 70:
            return "LOW"
        if player_score >= 68:
            return "HIGH"
        if player_score >= 45:
            return "MEDIUM"
        return "LOW"

    def compute_recommendations(
        self,
        league_id: str,
        roster_id: int,
    ) -> WaiverRecommendationsResponse:
        state = get_faab_state(self._conn, league_id, roster_id)
        direction_label = self._direction_label(league_id, roster_id)
        direction_urgency = DIRECTION_URGENCY.get(direction_label, 0.55)
        weak_positions, starter_requirements, roster_counts = self._roster_needs(
            league_id,
            roster_id,
        )
        position_limits = self._position_limits(league_id)
        available_ids = get_available_players(self._conn, league_id)
        player_rows = self._player_rows(available_ids)
        stats_map = self._stats_map(available_ids)
        adp_map = self._adp_map(available_ids)
        drop_candidates = self._drop_candidates(league_id, roster_id)
        league_median_remaining = self._league_median_remaining(
            league_id,
            int(state["total_budget"] or 100),
        )

        recommendations: list[tuple[float, WaiverRecommendation]] = []
        for player in player_rows:
            player_id = str(player["player_id"])
            position = str(player["position"])
            position_limit = position_limits.get(position)
            if position_limit is not None and roster_counts.get(position, 0) >= position_limit:
                continue
            player_score, positional_scarcity, is_immediate_start = self._score_available_player(
                player,
                weak_positions=weak_positions,
                starter_requirements=starter_requirements,
                direction_label=direction_label,
                avg_points=stats_map.get(player_id),
                adp=adp_map.get(player_id),
            )

            waiver_type_label = str(state["waiver_type_label"])
            if waiver_type_label == "rolling":
                bid_low = bid_mid = bid_high = None
                recommendation_label = "rolling_waiver"
            elif waiver_type_label == "faab":
                bid_low, bid_mid, bid_high = compute_bid_range(
                    player_score,
                    int(state["remaining_faab"] or 0),
                    league_median_remaining,
                    direction_urgency,
                    positional_scarcity,
                    is_immediate_start,
                )
                recommendation_label = "faab_bid" if bid_high > 0 else "free_agent_only"
            else:
                bid_low, bid_mid, bid_high = (0, 0, 0)
                recommendation_label = "free_agent_only"

            urgency = self._urgency_label(
                recommendation_label,
                bid_mid if isinstance(bid_mid, int) else None,
                int(state["remaining_faab"]) if state["remaining_faab"] is not None else None,
                player_score,
            )
            rationale = (
                f"{player['player_name']} fits a {_format_direction(direction_label)} build "
                f"and addresses {player['position']} depth."
            )
            drop_candidate = drop_candidates[0] if drop_candidates else None
            age = player.get("age")
            roster_fit = self._roster_fit_label(
                position=str(player["position"]),
                weak_positions=weak_positions,
                is_immediate_start=is_immediate_start,
                age=int(age) if age is not None else None,
            )
            recommendation = WaiverRecommendation(
                player_id=player_id,
                player_name=str(player["player_name"]),
                position=str(player["position"]),
                team=player["team"],
                recommendation_label=recommendation_label,
                bid_low=bid_low,
                bid_mid=bid_mid,
                bid_high=bid_high,
                urgency=urgency,
                rationale=rationale,
                is_immediate_start=is_immediate_start,
                drop_candidate=drop_candidate["player_name"] if drop_candidate else None,
                drop_candidate_player_id=drop_candidate["player_id"] if drop_candidate else None,
                drop_reason=(
                    f"{drop_candidate['player_name']} is the preferred drop: "
                    f"{drop_candidate['reason']}."
                    if drop_candidate
                    else None
                ),
                roster_fit=roster_fit,
                dynasty_stash=roster_fit == "Dynasty stash",
                confidence=self._confidence_label(
                    player_score=player_score,
                    data_freshness_warning=bool(state["data_freshness_warning"]),
                ),
                data_freshness_warning=bool(state["data_freshness_warning"]),
                hours_since_ingest=state["hours_since_ingest"],
            )
            sort_score = float(bid_mid or player_score)
            recommendations.append((sort_score, recommendation))

        recommendations.sort(
            key=lambda item: (
                item[1].is_immediate_start,
                item[1].urgency == "High",
                item[0],
            ),
            reverse=True,
        )

        result = WaiverRecommendationsResponse(
            league_id=league_id,
            roster_id=roster_id,
            waiver_type_label=str(state["waiver_type_label"]),
            waiver_type_raw=int(state["waiver_type_raw"]),
            remaining_faab=int(state["remaining_faab"]) if state["remaining_faab"] is not None else None,
            total_faab=int(state["total_budget"]) if state["total_budget"] is not None else None,
            recommendations=[recommendation for _, recommendation in recommendations[:12]],
            data_freshness_warning=bool(state["data_freshness_warning"]),
            computed_at=datetime.now(timezone.utc).isoformat(),
        )
        result.recommendation_cards = self._card_engine.build_waiver_cards(
            result.recommendations,
            league_id,
        )
        return result
 
__all__ = [
    "WaiverEngine",
    "compute_bid_range",
    "get_available_players",
    "get_faab_state",
]

from __future__ import annotations

from collections.abc import Iterable
import math
from typing import Any

import duckdb

from fantasy.trends.constants import ADP_TIER_BINS, SIMILARITY_COMPONENTS
from fantasy.trends.models import SimilarPlayer
from fantasy.trends.trend_engine import TrendEngine
from fantasy.trends.trend_repo import TrendRepo


def _adp_tier(adp: float | None) -> int:
    if adp is None:
        return len(ADP_TIER_BINS)
    for index, (low, high) in enumerate(ADP_TIER_BINS):
        if low <= adp <= high:
            return index
    return len(ADP_TIER_BINS)


def _context_label(target: dict[str, object], candidate: dict[str, object]) -> str:
    feature_labels = {
        "comp_age_curve": "age curve",
        "comp_ceiling": "ceiling",
        "comp_floor": "floor",
        "comp_role_stability": "role stability",
        "comp_short_term": "short-term outlook",
    }
    closest = sorted(
        SIMILARITY_COMPONENTS,
        key=lambda component: abs(
            float(target.get(component) or 0.0) - float(candidate.get(component) or 0.0)
        ),
    )[:2]
    feature_text = " and ".join(feature_labels[component] for component in closest)
    return (
        f"age {int(candidate.get('age') or 24)} {candidate.get('position') or 'UNKNOWN'}, "
        f"similar {feature_text}"
    )


def find_similar_players(
    player_id: str,
    conn: duckdb.DuckDBPyConnection,
    n: int = 3,
) -> list[SimilarPlayer]:
    engine = TrendEngine(conn)
    repo = TrendRepo(conn)
    candidates = repo.list_candidate_players()
    snapshots = engine.current_snapshots(
        [str(candidate["player_id"]) for candidate in candidates]
    )
    return find_similar_players_from_snapshots(player_id, snapshots.values(), n=n)


def find_similar_players_from_snapshots(
    player_id: str,
    snapshots: Iterable[dict[str, Any]],
    n: int = 3,
) -> list[SimilarPlayer]:
    snapshot_by_player_id = {
        str(snapshot["player_id"]): snapshot
        for snapshot in snapshots
        if snapshot.get("player_id") is not None
    }
    target = snapshot_by_player_id.get(player_id)
    if target is None:
        return []

    scored: list[tuple[float, dict[str, object]]] = []
    target_tier = _adp_tier(target.get("startup_adp"))  # type: ignore[arg-type]
    for candidate_id, snapshot in snapshot_by_player_id.items():
        if candidate_id == player_id:
            continue
        if snapshot.get("position") != target.get("position"):
            continue
        if abs(_adp_tier(snapshot.get("startup_adp")) - target_tier) > 1:  # type: ignore[arg-type]
            continue

        distance = 0.0
        for component in SIMILARITY_COMPONENTS:
            target_value = float(target.get(component) or 0.0)
            candidate_value = float(snapshot.get(component) or 0.0)
            distance += (target_value - candidate_value) ** 2
        distance += (abs(float(target.get("age") or 24) - float(snapshot.get("age") or 24)) / 20.0) ** 2
        scored.append((math.sqrt(distance), snapshot))

    if not scored:
        return []

    scored.sort(key=lambda item: item[0])
    max_distance = max(item[0] for item in scored) or 1.0
    results: list[SimilarPlayer] = []
    for distance, snapshot in scored[: max(int(n), 0)]:
        similarity = max(0.0, 1.0 - distance / max_distance)
        results.append(
            SimilarPlayer(
                player_id=str(snapshot["player_id"]),
                player_name=str(snapshot.get("full_name") or snapshot["player_id"]),
                similarity_score=round(similarity, 2),
                archetype_label=None,
                context=_context_label(target, snapshot),
            )
        )
    return results

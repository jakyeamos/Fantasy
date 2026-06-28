from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus

import duckdb

from fantasy.edge_radar.models import (
    EdgeRadarItem,
    EdgeRadarResponse,
    EdgeSignalType,
    SimilarPlayerOutcome,
    SourceHealth,
)
from fantasy.portfolio.portfolio_repo import PortfolioRepo

MIN_PLAYER_DELTA = 0.10
BUY_HIGH_MARKET_PRICE = 0.70
SELL_HIGH_MARKET_PRICE = 0.55


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


class EdgeRadarEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn
        self._portfolio_repo = PortfolioRepo(conn)

    def build(
        self,
        *,
        league_id: str | None = None,
        signal_type: EdgeSignalType | None = None,
        limit: int = 50,
    ) -> EdgeRadarResponse:
        source_health = self._source_health()
        items = self._player_delta_items(league_id)
        items.extend(self._waiver_items(league_id))
        if signal_type is not None:
            items = [item for item in items if item.signal_type == signal_type]
        items.sort(
            key=lambda item: (
                -abs(item.market_delta),
                -item.conviction_score,
                item.player_name.lower(),
                item.id,
            )
        )
        bounded = items[: max(1, limit)]
        degraded_sources = [
            source for source in source_health if source.status != "ready"
        ]
        return EdgeRadarResponse(
            items=bounded,
            source_health=source_health,
            total=len(bounded),
            computed_at=datetime.now(timezone.utc).isoformat(),
            status="degraded" if degraded_sources else "ok",
            degraded_reason=(
                "Some Edge Radar sources are unavailable: "
                + ", ".join(source.source for source in degraded_sources)
                if degraded_sources
                else None
            ),
        )

    def _player_delta_items(self, league_id: str | None) -> list[EdgeRadarItem]:
        rows = self._conn.execute(
            """
            SELECT pv.league_id,
                   pv.player_id,
                   COALESCE(p.full_name, pv.player_id),
                   COALESCE(p.position, 'UNKNOWN'),
                   COALESCE(p.team, ''),
                   p.age,
                   p.metadata_blob,
                   COALESCE(
                       pv.lens_production,
                       pv.lens_direction,
                       pv.comp_current_production,
                       0.5
                   ),
                   COALESCE(pv.lens_market, 0.5),
                   COALESCE(adp.adp, 250.0),
                   COALESCE(pv.comp_role_stability, 0.5),
                   COALESCE(pv.comp_ceiling, 0.5),
                   COALESCE(pv.comp_floor, 0.5)
            FROM player_values pv
            LEFT JOIN players p ON p.player_id = pv.player_id
            LEFT JOIN player_adp_baseline adp ON adp.player_id = pv.player_id
            WHERE (? IS NULL OR pv.league_id = ?)
            """,
            [league_id, league_id],
        ).fetchall()
        ownership = self._ownership_context(league_id)
        user_rosters = {
            str(row["league_id"]): int(row["roster_id"])
            for row in self._portfolio_repo._portfolio_roster_rows()
        }
        items: list[EdgeRadarItem] = []
        for row in rows:
            player_id = str(row[1])
            model_value = _clamp01(float(row[7] or 0.5))
            market_price = _clamp01(float(row[8] or 0.5))
            market_delta = round(model_value - market_price, 2)
            if abs(market_delta) < MIN_PLAYER_DELTA:
                continue
            row_league_id = str(row[0])
            owner_roster_id = ownership.get((row_league_id, player_id))
            user_roster_id = user_rosters.get(row_league_id)
            signal_type = self._signal_type(
                market_delta=market_delta,
                market_price=market_price,
                owned_by_user=owner_roster_id == user_roster_id,
            )
            comps = self._similar_player_outcomes(
                player_id=player_id,
                position=str(row[3]),
                team=str(row[4] or ""),
                age=int(row[5]) if row[5] is not None else None,
                metadata=_loads(row[6], {}),
                model_value=model_value,
                market_price=market_price,
                role_stability=_clamp01(float(row[10] or 0.5)),
                ceiling=_clamp01(float(row[11] or 0.5)),
                floor=_clamp01(float(row[12] or 0.5)),
            )
            similarity_evidence = (
                [
                    "Similarity: "
                    f"{comps[0].player_name} {comps[0].similarity_score:.2f} - "
                    f"{comps[0].outcome_summary}"
                ]
                if comps
                else []
            )
            items.append(
                EdgeRadarItem(
                    id=f"{signal_type}:{row_league_id}:{player_id}",
                    signal_type=signal_type,
                    league_id=row_league_id,
                    roster_id=user_roster_id,
                    player_id=player_id,
                    player_name=str(row[2]),
                    position=str(row[3]),
                    action_label=self._action_label(signal_type),
                    market_delta=market_delta,
                    market_price=round(market_price, 2),
                    model_value=round(model_value, 2),
                    conviction_score=self._conviction_score(
                        market_delta=market_delta,
                        market_price=market_price,
                        owner_roster_id=owner_roster_id,
                        user_roster_id=user_roster_id,
                    ),
                    confidence=self._confidence(abs(market_delta)),
                    acceptable_price=self._acceptable_price(signal_type, market_delta),
                    timing_window=self._timing_window(signal_type),
                    source_evidence=[
                        f"Market delta: {market_delta:+.2f}",
                        f"Model value: {model_value:.2f}",
                        f"Market price: {market_price:.2f}",
                        f"Startup ADP: {float(row[9] or 250.0):.1f}",
                    ]
                    + similarity_evidence,
                    similarity_score=comps[0].similarity_score if comps else 0.0,
                    similar_player_outcomes=comps,
                    risks=self._risks(signal_type),
                    cta_label=(
                        "Open Trade Lab"
                        if signal_type in {"buy_low", "buy_high", "sell_high", "sell_low"}
                        else "Open Edge Radar"
                    ),
                    cta_destination=self._trade_destination(
                        signal_type=signal_type,
                        league_id=row_league_id,
                        user_roster_id=user_roster_id,
                        owner_roster_id=owner_roster_id,
                        player_id=player_id,
                        player_name=str(row[2]),
                        position=str(row[3]),
                    ),
                )
            )
        return items

    def _similar_player_outcomes(
        self,
        *,
        player_id: str,
        position: str,
        team: str,
        age: int | None,
        metadata: dict[str, Any],
        model_value: float,
        market_price: float,
        role_stability: float,
        ceiling: float,
        floor: float,
    ) -> list[SimilarPlayerOutcome]:
        rows = self._conn.execute(
            """
            SELECT p.player_id,
                   COALESCE(p.full_name, p.player_id),
                   COALESCE(p.position, 'UNKNOWN'),
                   COALESCE(p.team, ''),
                   p.age,
                   p.metadata_blob,
                   COALESCE(
                       pv.lens_production,
                       pv.lens_direction,
                       pv.comp_current_production,
                       0.5
                   ),
                   COALESCE(pv.lens_market, 0.5),
                   COALESCE(pv.comp_role_stability, 0.5),
                   COALESCE(pv.comp_ceiling, 0.5),
                   COALESCE(pv.comp_floor, 0.5),
                   AVG(ps.fantasy_points) AS avg_points,
                   COUNT(ps.player_id) AS stat_games
            FROM players p
            JOIN player_values pv ON pv.player_id = p.player_id
            LEFT JOIN player_stats_weekly ps ON ps.player_id = p.player_id
            WHERE p.player_id != ?
              AND COALESCE(p.position, 'UNKNOWN') = ?
            GROUP BY p.player_id, p.full_name, p.position, p.team, p.age, p.metadata_blob,
                     pv.lens_production, pv.lens_direction, pv.comp_current_production,
                     pv.lens_market, pv.comp_role_stability, pv.comp_ceiling, pv.comp_floor
            LIMIT 80
            """,
            [player_id, position],
        ).fetchall()
        outcomes: list[SimilarPlayerOutcome] = []
        for row in rows:
            comp_metadata = _loads(row[5], {})
            score = self._similarity_score(
                team=team,
                age=age,
                metadata=metadata,
                model_value=model_value,
                market_price=market_price,
                role_stability=role_stability,
                ceiling=ceiling,
                floor=floor,
                comp_team=str(row[3] or ""),
                comp_age=int(row[4]) if row[4] is not None else None,
                comp_metadata=comp_metadata,
                comp_model_value=_clamp01(float(row[6] or 0.5)),
                comp_market_price=_clamp01(float(row[7] or 0.5)),
                comp_role_stability=_clamp01(float(row[8] or 0.5)),
                comp_ceiling=_clamp01(float(row[9] or 0.5)),
                comp_floor=_clamp01(float(row[10] or 0.5)),
            )
            if score < 0.45:
                continue
            outcomes.append(
                SimilarPlayerOutcome(
                    player_id=str(row[0]),
                    player_name=str(row[1]),
                    similarity_score=round(score, 2),
                    context=self._similarity_context(
                        team=team,
                        metadata=metadata,
                        comp_team=str(row[3] or ""),
                        comp_metadata=comp_metadata,
                        comp_age=int(row[4]) if row[4] is not None else None,
                    ),
                    outcome_summary=self._outcome_summary(
                        avg_points=float(row[11]) if row[11] is not None else None,
                        stat_games=int(row[12] or 0),
                        model_value=_clamp01(float(row[6] or 0.5)),
                        market_price=_clamp01(float(row[7] or 0.5)),
                    ),
                )
            )
        outcomes.sort(key=lambda outcome: (-outcome.similarity_score, outcome.player_name))
        return outcomes[:3]

    def _similarity_score(
        self,
        *,
        team: str,
        age: int | None,
        metadata: dict[str, Any],
        model_value: float,
        market_price: float,
        role_stability: float,
        ceiling: float,
        floor: float,
        comp_team: str,
        comp_age: int | None,
        comp_metadata: dict[str, Any],
        comp_model_value: float,
        comp_market_price: float,
        comp_role_stability: float,
        comp_ceiling: float,
        comp_floor: float,
    ) -> float:
        score = 0.35
        if age is not None and comp_age is not None:
            score += max(0.0, 0.20 - abs(age - comp_age) * 0.04)
        profile_distance = (
            abs(model_value - comp_model_value)
            + abs(market_price - comp_market_price)
            + abs(role_stability - comp_role_stability)
            + abs(ceiling - comp_ceiling)
            + abs(floor - comp_floor)
        ) / 5.0
        score += max(0.0, 0.25 - (profile_distance * 0.5))
        if team and team == comp_team:
            score += 0.08
        for key in ("offensive_system", "head_coach", "offensive_coordinator"):
            if metadata.get(key) and metadata.get(key) == comp_metadata.get(key):
                score += 0.04
        return _clamp01(score)

    def _similarity_context(
        self,
        *,
        team: str,
        metadata: dict[str, Any],
        comp_team: str,
        comp_metadata: dict[str, Any],
        comp_age: int | None,
    ) -> str:
        parts: list[str] = []
        if comp_age is not None:
            parts.append(f"age {comp_age}")
        if team and team == comp_team:
            parts.append("same NFL team")
        if metadata.get("offensive_system") and metadata.get(
            "offensive_system"
        ) == comp_metadata.get("offensive_system"):
            parts.append("same offensive system")
        if metadata.get("head_coach") and metadata.get("head_coach") == comp_metadata.get(
            "head_coach"
        ):
            parts.append("same head coach")
        if metadata.get("offensive_coordinator") and metadata.get(
            "offensive_coordinator"
        ) == comp_metadata.get("offensive_coordinator"):
            parts.append("same offensive coordinator")
        if not parts:
            parts.append("similar value and role profile")
        return ", ".join(parts)

    def _outcome_summary(
        self,
        *,
        avg_points: float | None,
        stat_games: int,
        model_value: float,
        market_price: float,
    ) -> str:
        if avg_points is not None and stat_games > 0:
            return (
                f"averaged {avg_points:.1f} fantasy points across "
                f"{stat_games} public stat games"
            )
        delta = model_value - market_price
        return (
            f"carried a {delta:+.2f} model-vs-market profile without "
            "public weekly outcome data"
        )

    def _waiver_items(self, league_id: str | None) -> list[EdgeRadarItem]:
        rows = self._conn.execute(
            """
            SELECT league_id, roster_id, recommendations_json
            FROM waiver_recommendations
            WHERE (? IS NULL OR league_id = ?)
            ORDER BY computed_at DESC
            """,
            [league_id, league_id],
        ).fetchall()
        items: list[EdgeRadarItem] = []
        for row in rows:
            payload = _loads(str(row[2]), {})
            recs = payload.get("recommendations") if isinstance(payload, dict) else []
            for rec in list(recs or [])[:3]:
                player_id = str(rec.get("player_id") or "")
                if not player_id:
                    continue
                bid_low = rec.get("bid_low")
                bid_high = rec.get("bid_high")
                confidence = str(rec.get("confidence") or "MEDIUM")
                market_delta = 0.14 if bool(rec.get("is_immediate_start")) else 0.10
                if confidence == "HIGH":
                    market_delta += 0.05
                items.append(
                    EdgeRadarItem(
                        id=f"waiver_pickup:{row[0]}:{row[1]}:{player_id}",
                        signal_type="waiver_pickup",
                        league_id=str(row[0]),
                        roster_id=int(row[1]),
                        player_id=player_id,
                        player_name=str(rec.get("player_name") or player_id),
                        position=str(rec.get("position") or "UNKNOWN"),
                        action_label="Waiver pickup",
                        market_delta=round(market_delta, 2),
                        market_price=0.0,
                        model_value=round(market_delta, 2),
                        conviction_score=round(market_delta * 100.0, 2),
                        confidence=(
                            confidence
                            if confidence in {"HIGH", "MEDIUM", "LOW"}
                            else "MEDIUM"
                        ),
                        acceptable_price=(
                            f"${bid_low or 0}-${bid_high or bid_low or 0} FAAB"
                            if rec.get("recommendation_label") != "free_agent_only"
                            else "Free claim"
                        ),
                        timing_window="Before the next waiver run.",
                        source_evidence=[
                            str(rec.get("rationale") or "Cached waiver recommendation."),
                            f"Roster fit: {rec.get('roster_fit') or 'Depth churn'}",
                        ],
                        risks=[
                            str(
                                rec.get("drop_reason")
                                or "Waiver role signal can reverse quickly."
                            )
                        ],
                        cta_label="Open Waiver Board",
                        cta_destination=(
                            f"/league/{row[0]}/waivers?rosterId={int(row[1])}"
                        ),
                    )
                )
        return items

    def _source_health(self) -> list[SourceHealth]:
        return [
            self._table_health("sleeper", ["leagues", "rosters", "players"]),
            self._table_health("fantasycalc", ["player_adp_baseline"]),
            self._table_health("nflreadpy", ["player_stats_weekly"]),
            self._table_health("local_prospect_csv", ["prospect_features"]),
            SourceHealth(
                source="manual_imports",
                status="missing",
                detail="No manual Edge Radar import table configured yet.",
                freshness=0.0,
            ),
            SourceHealth(
                source="api_key_sources",
                status="missing",
                detail="No API-key Edge Radar adapters configured yet.",
                freshness=0.0,
            ),
            SourceHealth(
                source="allowlisted_scrapers",
                status="missing",
                detail="No allowlisted scraper adapters configured yet.",
                freshness=0.0,
            ),
        ]

    def _table_health(self, source: str, tables: list[str]) -> SourceHealth:
        counts: list[int] = []
        for table in tables:
            try:
                row = self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            except Exception:
                counts.append(0)
                continue
            counts.append(int(row[0]) if row else 0)
        ready = all(count > 0 for count in counts)
        return SourceHealth(
            source=source,
            status="ready" if ready else "missing",
            detail=(
                f"{source} source has data in {', '.join(tables)}."
                if ready
                else f"{source} source is missing data in at least one required table."
            ),
            freshness=1.0 if ready else 0.0,
        )

    def _ownership_context(
        self,
        league_id: str | None,
    ) -> dict[tuple[str, str], int]:
        rows = self._conn.execute(
            """
            SELECT league_id, roster_id, players
            FROM rosters
            WHERE (? IS NULL OR league_id = ?)
            """,
            [league_id, league_id],
        ).fetchall()
        ownership: dict[tuple[str, str], int] = {}
        for row in rows:
            for player_id in _loads(row[2], []):
                if player_id not in (None, "", 0, "0"):
                    ownership[(str(row[0]), str(player_id))] = int(row[1])
        return ownership

    def _signal_type(
        self,
        *,
        market_delta: float,
        market_price: float,
        owned_by_user: bool,
    ) -> EdgeSignalType:
        if market_delta > 0:
            return "buy_high" if market_price >= BUY_HIGH_MARKET_PRICE else "buy_low"
        if owned_by_user:
            return "sell_high" if market_price >= SELL_HIGH_MARKET_PRICE else "sell_low"
        return "sell_high" if market_price >= SELL_HIGH_MARKET_PRICE else "sell_low"

    def _conviction_score(
        self,
        *,
        market_delta: float,
        market_price: float,
        owner_roster_id: int | None,
        user_roster_id: int | None,
    ) -> float:
        base = abs(market_delta) * 100.0
        execution = 1.0
        if owner_roster_id is not None and user_roster_id is not None:
            execution = 1.1 if owner_roster_id != user_roster_id else 1.0
        source_agreement = 1.05 if market_price not in {0.0, 0.5} else 0.9
        return round(base * execution * source_agreement, 2)

    def _confidence(self, delta: float) -> str:
        if delta >= 0.25:
            return "HIGH"
        if delta >= 0.15:
            return "MEDIUM"
        return "LOW"

    def _action_label(self, signal_type: EdgeSignalType) -> str:
        return {
            "buy_low": "Buy low",
            "buy_high": "Buy high",
            "sell_high": "Sell high",
            "sell_low": "Sell low",
            "waiver_pickup": "Waiver pickup",
            "draft_diamond": "Draft diamond",
            "portfolio_hedge": "Portfolio hedge",
            "manager_exploit": "Manager exploit",
        }[signal_type]

    def _acceptable_price(self, signal_type: EdgeSignalType, delta: float) -> str:
        if signal_type == "buy_low":
            return f"Keep at least {abs(delta):.2f} normalized points of discount."
        if signal_type == "buy_high":
            return "Pay market only if the asset keeps scarcity or future-value leverage."
        if signal_type == "sell_high":
            return f"Capture the {abs(delta):.2f} normalized market premium."
        if signal_type == "sell_low":
            return "Exit at a fair market offer before the model gap widens."
        return "Use current market as the ceiling."

    def _timing_window(self, signal_type: EdgeSignalType) -> str:
        if signal_type in {"buy_low", "buy_high"}:
            return "This week before market reprices."
        if signal_type in {"sell_high", "sell_low"}:
            return "This week while liquidity still exists."
        return "Act before the next transaction window closes."

    def _risks(self, signal_type: EdgeSignalType) -> list[str]:
        if signal_type in {"buy_low", "buy_high"}:
            return ["The public market may be correctly discounting hidden role or injury risk."]
        if signal_type in {"sell_high", "sell_low"}:
            return ["Selling can be wrong if the market is early and the model is slow to adjust."]
        return ["Signal depends on cached recommendation freshness."]

    def _trade_destination(
        self,
        *,
        signal_type: EdgeSignalType,
        league_id: str,
        user_roster_id: int | None,
        owner_roster_id: int | None,
        player_id: str,
        player_name: str,
        position: str,
    ) -> str:
        if signal_type not in {"buy_low", "buy_high", "sell_high", "sell_low"}:
            return "/edge-radar"
        params = [f"leagueId={quote_plus(league_id)}"]
        if user_roster_id is not None:
            params.append(f"userRosterId={user_roster_id}")
        if owner_roster_id is not None and owner_roster_id != user_roster_id:
            params.append(f"counterpartyRosterId={owner_roster_id}")
        encoded_name = quote_plus(player_name)
        encoded_position = quote_plus(position)
        if signal_type in {"buy_low", "buy_high"}:
            params.extend(
                [
                    f"receivePlayerId={quote_plus(player_id)}",
                    f"receivePlayerName={encoded_name}",
                    f"receivePlayerPosition={encoded_position}",
                    f"targetPlayerId={quote_plus(player_id)}",
                    f"targetPlayerName={encoded_name}",
                    f"targetPlayerPosition={encoded_position}",
                ]
            )
        else:
            params.extend(
                [
                    f"sendPlayerId={quote_plus(player_id)}",
                    f"sendPlayerName={encoded_name}",
                    f"sendPlayerPosition={encoded_position}",
                ]
            )
        return f"/trades?{'&'.join(params)}"


__all__ = ["EdgeRadarEngine"]

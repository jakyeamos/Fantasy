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
    SourceHealth,
)
from fantasy.edge_radar.similarity import (
    clamp01,
    merge_context_metadata,
    similar_player_outcomes,
    team_context_from_row,
    value_gain_evidence,
)
from fantasy.portfolio.portfolio_repo import PortfolioRepo

MIN_PLAYER_DELTA = 0.10
BUY_HIGH_MARKET_PRICE = 0.70
SELL_HIGH_MARKET_PRICE = 0.55


def _clamp01(value: float) -> float:
    return clamp01(value)


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _team_context_evidence(metadata: dict[str, Any]) -> list[str]:
    offensive_system = metadata.get("offensive_system")
    if not offensive_system:
        return []
    parts = [str(offensive_system)]
    if metadata.get("head_coach"):
        parts.append(f"HC {metadata['head_coach']}")
    if metadata.get("offensive_coordinator"):
        parts.append(f"OC {metadata['offensive_coordinator']}")
    return [f"Team context: {', '.join(parts)}"]


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
        items = self._player_delta_items(league_id, limit=max(1, limit))
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

    def _player_delta_items(
        self,
        league_id: str | None,
        limit: int,
    ) -> list[EdgeRadarItem]:
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
                   COALESCE(pv.comp_floor, 0.5),
                   TRY_CAST(l.season AS INTEGER),
                   tc.head_coach,
                   tc.offensive_coordinator,
                   tc.play_caller,
                   tc.offensive_system,
                   tc.pace_label,
                   tc.pass_rate_label
            FROM player_values pv
            LEFT JOIN players p ON p.player_id = pv.player_id
            LEFT JOIN leagues l ON l.league_id = pv.league_id
            LEFT JOIN player_adp_baseline adp ON adp.player_id = pv.player_id
            LEFT JOIN team_context_by_season tc
              ON tc.team = p.team
             AND tc.season = TRY_CAST(l.season AS INTEGER)
            WHERE (? IS NULL OR pv.league_id = ?)
            """,
            [league_id, league_id],
        ).fetchall()
        ownership = self._ownership_context(league_id)
        user_rosters = {
            str(row["league_id"]): int(row["roster_id"])
            for row in self._portfolio_repo._portfolio_roster_rows()
        }
        candidates: list[dict[str, Any]] = []
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
            player_name = str(row[2])
            conviction_score = self._conviction_score(
                market_delta=market_delta,
                market_price=market_price,
                owner_roster_id=owner_roster_id,
                user_roster_id=user_roster_id,
            )
            metadata = merge_context_metadata(
                _loads(row[6], {}),
                team_context_from_row(row, 14),
            )
            candidate_id = f"{signal_type}:{row_league_id}:{player_id}"
            candidates.append(
                {
                    "id": candidate_id,
                    "signal_type": signal_type,
                    "league_id": row_league_id,
                    "roster_id": user_roster_id,
                    "owner_roster_id": owner_roster_id,
                    "player_id": player_id,
                    "player_name": player_name,
                    "position": str(row[3]),
                    "team": str(row[4] or ""),
                    "age": int(row[5]) if row[5] is not None else None,
                    "metadata": metadata,
                    "model_value": model_value,
                    "market_price": market_price,
                    "market_delta": market_delta,
                    "startup_adp": float(row[9] or 250.0),
                    "role_stability": _clamp01(float(row[10] or 0.5)),
                    "ceiling": _clamp01(float(row[11] or 0.5)),
                    "floor": _clamp01(float(row[12] or 0.5)),
                    "season": int(row[13]) if row[13] is not None else None,
                    "conviction_score": conviction_score,
                }
            )

        candidates.sort(
            key=lambda candidate: (
                -abs(float(candidate["market_delta"])),
                -float(candidate["conviction_score"]),
                str(candidate["player_name"]).lower(),
                str(candidate["id"]),
            )
        )

        items: list[EdgeRadarItem] = []
        for candidate in candidates[:limit]:
            signal_type = candidate["signal_type"]
            metadata = candidate["metadata"]
            model_value = float(candidate["model_value"])
            market_price = float(candidate["market_price"])
            comps = similar_player_outcomes(
                self._conn,
                league_id=str(candidate["league_id"]),
                season=candidate["season"],
                player_id=str(candidate["player_id"]),
                position=str(candidate["position"]),
                team=str(candidate["team"]),
                age=candidate["age"],
                metadata=metadata,
                model_value=model_value,
                market_price=market_price,
                role_stability=float(candidate["role_stability"]),
                ceiling=float(candidate["ceiling"]),
                floor=float(candidate["floor"]),
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
                    id=str(candidate["id"]),
                    signal_type=signal_type,
                    league_id=str(candidate["league_id"]),
                    roster_id=candidate["roster_id"],
                    player_id=str(candidate["player_id"]),
                    player_name=str(candidate["player_name"]),
                    position=str(candidate["position"]),
                    action_label=self._action_label(signal_type),
                    market_delta=float(candidate["market_delta"]),
                    market_price=round(market_price, 2),
                    model_value=round(model_value, 2),
                    conviction_score=float(candidate["conviction_score"]),
                    confidence=self._confidence(abs(float(candidate["market_delta"]))),
                    acceptable_price=self._acceptable_price(
                        signal_type,
                        float(candidate["market_delta"]),
                    ),
                    timing_window=self._timing_window(signal_type),
                    source_evidence=[
                        f"Market delta: {float(candidate['market_delta']):+.2f}",
                        f"Model value: {model_value:.2f}",
                        f"Market price: {market_price:.2f}",
                        f"Startup ADP: {float(candidate['startup_adp']):.1f}",
                    ]
                    + _team_context_evidence(metadata)
                    + similarity_evidence
                    + value_gain_evidence(
                        [comp.outcome_summary for comp in comps]
                    ),
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
                        league_id=str(candidate["league_id"]),
                        user_roster_id=candidate["roster_id"],
                        owner_roster_id=candidate["owner_roster_id"],
                        player_id=str(candidate["player_id"]),
                        player_name=str(candidate["player_name"]),
                        position=str(candidate["position"]),
                    ),
                )
            )
        return items

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
            self._table_health("manual_imports", ["team_context_by_season"]),
            self._team_context_health(
                source="team_context_curated",
                where_clause="""
                    head_coach IS NOT NULL
                    OR offensive_coordinator IS NOT NULL
                    OR play_caller IS NOT NULL
                    OR offensive_system IS NOT NULL
                """,
            ),
            self._team_context_health(
                source="team_environment_nflreadpy",
                where_clause="""
                    source = 'team_environment_nflreadpy'
                    AND (pace_label IS NOT NULL OR pass_rate_label IS NOT NULL)
                """,
            ),
            self._metadata_health(
                source="player_usage_metadata",
                required_markers=('"target_share"', '"carry_share"', '"weekly_targets"'),
            ),
            self._metadata_health(
                source="player_market_metadata",
                required_markers=('"trade_value_movement"',),
            ),
            self._metadata_health(
                source="player_dense_metadata",
                required_markers=(
                    '"yards_per_route_run"',
                    '"route_participation"',
                    '"snap_share"',
                    '"first_read_target_share"',
                ),
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

    def _metadata_health(
        self,
        *,
        source: str,
        required_markers: tuple[str, ...],
    ) -> SourceHealth:
        clauses = " OR ".join("metadata_blob LIKE ?" for _ in required_markers)
        try:
            row = self._conn.execute(
                f"""
                SELECT COUNT(*), MAX(refreshed_at)
                FROM players
                WHERE metadata_blob IS NOT NULL
                  AND ({clauses})
                """,
                [f"%{marker}%" for marker in required_markers],
            ).fetchone()
        except Exception:
            row = None
        count = int(row[0]) if row and row[0] is not None else 0
        refreshed_at = row[1] if row and row[1] is not None else None
        ready = count > 0
        return SourceHealth(
            source=source,
            status="ready" if ready else "missing",
            detail=(
                f"{source} has {count} enriched players; latest refresh {refreshed_at}."
                if ready
                else f"{source} has no enriched player metadata rows."
            ),
            freshness=1.0 if ready else 0.0,
        )

    def _team_context_health(self, *, source: str, where_clause: str) -> SourceHealth:
        try:
            row = self._conn.execute(
                f"""
                SELECT COUNT(*), MAX(loaded_at)
                FROM team_context_by_season
                WHERE {where_clause}
                """
            ).fetchone()
        except Exception:
            row = None
        count = int(row[0]) if row and row[0] is not None else 0
        loaded_at = row[1] if row and row[1] is not None else None
        ready = count > 0
        return SourceHealth(
            source=source,
            status="ready" if ready else "missing",
            detail=(
                f"{source} has {count} rows; latest load {loaded_at}."
                if ready
                else f"{source} has no loaded team context rows."
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

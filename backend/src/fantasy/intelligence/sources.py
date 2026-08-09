from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from uuid import uuid4

import duckdb

from fantasy.intelligence.fresh_models import (
    EventType,
    ExtractedEventClaim,
    ParseStatus,
    SourceObservation,
    SourceOutcome,
    SourceTier,
)


def _records(frame: Any) -> list[dict[str, Any]]:
    if frame is None:
        return []
    if hasattr(frame, "to_dicts"):
        return list(frame.to_dicts())
    if hasattr(frame, "to_dict"):
        return list(frame.to_dict("records"))
    return list(frame)


def _content_hash(source_id: str, payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(f"{source_id}:{raw}".encode()).hexdigest()


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def _first(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


@dataclass
class SourceBatch:
    source_id: str
    domain: str
    observations: list[SourceObservation] = field(default_factory=list)
    claims: list[tuple[SourceObservation, ExtractedEventClaim]] = field(default_factory=list)
    outcome: SourceOutcome | None = None
    authoritative_empty: bool = False
    coverage_through: datetime | None = None


class PlayerIdentityIndex:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        rows = conn.execute(
            "SELECT player_id, full_name, team FROM players"
        ).fetchall()
        self._by_name = {
            str(row[1]).casefold().strip(): str(row[0])
            for row in rows
            if row[1]
        }
        self._by_id = {str(row[0]): str(row[0]) for row in rows}

    def resolve(self, row: dict[str, Any]) -> tuple[str | None, str | None]:
        raw_id = _first(row, "player_id", "gsis_id", "sleeper_id", "pfr_id")
        name = _first(row, "full_name", "player_name", "name", "player")
        if raw_id is not None and str(raw_id) in self._by_id:
            return str(raw_id), str(name) if name else None
        if name is not None:
            return self._by_name.get(str(name).casefold().strip()), str(name)
        return None, None


class NflreadpySource:
    """Structured public football evidence. Each dataset fails independently."""

    def __init__(self, conn: duckdb.DuckDBPyConnection, run_id: str, season: int) -> None:
        self._conn = conn
        self._run_id = run_id
        self._season = season
        self._identities = PlayerIdentityIndex(conn)

    def collect(self, source_ids: set[str] | None = None) -> list[SourceBatch]:
        try:
            import nflreadpy
        except ImportError:
            return [self._failed(source_id, domain, "nflreadpy is not installed") for source_id, domain in (
                ("nflreadpy:injuries", "injuries"),
                ("nflreadpy:depth_charts", "depth_chart"),
                ("nflreadpy:snaps", "usage"),
                ("nflreadpy:opportunity", "usage"),
                ("nflreadpy:weekly_rosters", "player_metadata"),
            ) if source_ids is None or source_id in source_ids]
        loaders: list[tuple[str, str, Callable[..., Any], Callable[[list[dict[str, Any]]], list[ExtractedEventClaim]]]] = [
            ("nflreadpy:injuries", "injuries", nflreadpy.load_injuries, self._injury_claims),
            ("nflreadpy:depth_charts", "depth_chart", nflreadpy.load_depth_charts, self._depth_claims),
            ("nflreadpy:snaps", "usage", nflreadpy.load_snap_counts, self._usage_claims),
            ("nflreadpy:opportunity", "usage", nflreadpy.load_ff_opportunity, self._usage_claims),
            ("nflreadpy:weekly_rosters", "player_metadata", nflreadpy.load_rosters_weekly, lambda rows: []),
        ]
        return [
            self._load(source_id, domain, loader, normalizer)
            for source_id, domain, loader, normalizer in loaders
            if source_ids is None or source_id in source_ids
        ]

    def _load(
        self,
        source_id: str,
        domain: str,
        loader: Callable[..., Any],
        normalizer: Callable[[list[dict[str, Any]]], list[ExtractedEventClaim]],
    ) -> SourceBatch:
        try:
            try:
                frame = loader([self._season])
            except TypeError:
                frame = loader(seasons=[self._season])
            rows = _records(frame)
        except Exception as exc:
            return self._failed(source_id, domain, f"{type(exc).__name__}: {exc}")
        claims = normalizer(rows)
        observed = datetime.now(timezone.utc)
        weeks = [_integer(_first(row, "week", "game_week")) for row in rows]
        max_week = max((week for week in weeks if week is not None), default=None)
        relevant_rows = rows
        if max_week is not None:
            relevant_rows = [row for row in rows if _integer(_first(row, "week", "game_week")) == max_week]
        evidence_payload = {
            "season": self._season,
            "coverage_week": max_week,
            "row_count": len(rows),
            "relevant_rows": relevant_rows[:250],
        }
        observation = SourceObservation(
            observation_id=str(uuid4()), run_id=self._run_id, source_id=source_id,
            source_tier=SourceTier.STRUCTURED,
            url="https://github.com/nflverse/nflverse-data",
            fetched_at=observed, observed_at=observed,
            coverage_through=observed, content_hash=_content_hash(source_id, evidence_payload),
            parse_status=ParseStatus.PARSED if rows else ParseStatus.EMPTY,
            evidence_excerpt=f"{len(rows)} structured rows; latest week {max_week or 'n/a'}",
            payload=evidence_payload, authoritative=True,
        )
        return SourceBatch(
            source_id=source_id, domain=domain, observations=[observation],
            claims=[(observation, claim) for claim in claims],
            outcome=SourceOutcome(source_id=source_id, status="complete", records_seen=len(rows),
                observations_written=1, events_written=len(claims)),
            authoritative_empty=not rows, coverage_through=observed,
        )

    def _failed(self, source_id: str, domain: str, message: str) -> SourceBatch:
        observed = datetime.now(timezone.utc)
        observation = SourceObservation(
            observation_id=str(uuid4()), run_id=self._run_id, source_id=source_id,
            source_tier=SourceTier.STRUCTURED, fetched_at=observed,
            content_hash=_content_hash(source_id, {"failure": message, "at": observed.isoformat()}),
            parse_status=ParseStatus.UNAVAILABLE, evidence_excerpt=message,
            payload={"error": message}, authoritative=True,
        )
        return SourceBatch(source_id=source_id, domain=domain, observations=[observation],
            outcome=SourceOutcome(source_id=source_id, status="failed", message=message))

    def _injury_claims(self, rows: list[dict[str, Any]]) -> list[ExtractedEventClaim]:
        if not rows:
            return []
        weeks = [_integer(_first(row, "week", "game_week")) for row in rows]
        max_week = max((week for week in weeks if week is not None), default=None)
        claims: list[ExtractedEventClaim] = []
        for row in rows:
            if max_week is not None and _integer(_first(row, "week", "game_week")) != max_week:
                continue
            status = str(_first(row, "report_status", "practice_status", "status") or "").strip()
            if not status:
                continue
            player_id, player_name = self._identities.resolve(row)
            team = _first(row, "team", "club")
            injury = _first(row, "report_primary_injury", "injury", "body_part")
            claims.append(ExtractedEventClaim(
                event_type=EventType.INJURY_STATUS, player_id=player_id,
                player_name=player_name, team=str(team) if team else None,
                effective_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=10),
                summary=f"{player_name or player_id or 'Unresolved player'}: {status}",
                details={"status": status, "injury": injury, "week": max_week},
            ))
        return claims

    def _depth_claims(self, rows: list[dict[str, Any]]) -> list[ExtractedEventClaim]:
        if not rows:
            return []
        weeks = [_integer(_first(row, "week", "game_week")) for row in rows]
        max_week = max((week for week in weeks if week is not None), default=None)
        claims: list[ExtractedEventClaim] = []
        for row in rows:
            if max_week is not None and _integer(_first(row, "week", "game_week")) != max_week:
                continue
            rank = _integer(_first(row, "depth_team", "depth_position", "depth_chart_order", "rank"))
            if rank is None:
                continue
            player_id, player_name = self._identities.resolve(row)
            team = _first(row, "team", "club")
            position = _first(row, "position", "pos_abb")
            claims.append(ExtractedEventClaim(
                event_type=EventType.DEPTH_CHART_ROLE, player_id=player_id,
                player_name=player_name, team=str(team) if team else None,
                effective_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=14),
                summary=f"{player_name or player_id or 'Unresolved player'} listed {position or ''}{rank}",
                details={"depth_rank": rank, "position": position, "week": max_week},
            ))
        return claims

    def _usage_claims(self, rows: list[dict[str, Any]]) -> list[ExtractedEventClaim]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            player_id, player_name = self._identities.resolve(row)
            key = player_id or (player_name or "").casefold()
            if key:
                grouped.setdefault(key, []).append(row)
        claims: list[ExtractedEventClaim] = []
        for player_rows in grouped.values():
            player_rows.sort(key=lambda row: _integer(_first(row, "week", "game_week")) or 0)
            if len(player_rows) < 2:
                continue
            before, after = player_rows[-2], player_rows[-1]
            before_share = _number(_first(before, "offense_pct", "snap_pct", "route_participation", "wopr"))
            after_share = _number(_first(after, "offense_pct", "snap_pct", "route_participation", "wopr"))
            if before_share is None or after_share is None:
                continue
            delta = after_share - before_share
            if abs(delta) < 0.15:
                continue
            player_id, player_name = self._identities.resolve(after)
            team = _first(after, "team", "club", "recent_team")
            claims.append(ExtractedEventClaim(
                event_type=EventType.USAGE_SHIFT, player_id=player_id, player_name=player_name,
                team=str(team) if team else None, effective_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=14),
                summary=f"{player_name or player_id or 'Unresolved player'} usage changed {delta:+.0%}",
                details={"before_share": before_share, "after_share": after_share,
                    "delta": delta, "week": _integer(_first(after, "week", "game_week"))},
            ))
        return claims


class LocalLeagueSource:
    """Turns already-ingested Sleeper transactions and FantasyCalc trends into events."""

    def __init__(self, conn: duckdb.DuckDBPyConnection, run_id: str) -> None:
        self._conn = conn
        self._run_id = run_id

    def collect(self, source_ids: set[str] | None = None) -> list[SourceBatch]:
        sources = {
            "sleeper:transactions": self._transactions,
            "fantasycalc:market_values": self._market,
        }
        return [
            collector()
            for source_id, collector in sources.items()
            if source_ids is None or source_id in source_ids
        ]

    def _transactions(self) -> SourceBatch:
        source_id = "sleeper:transactions"
        rows = self._conn.execute(
            """
            SELECT transaction_id, league_id, type, status, created_at, adds, drops
            FROM transactions
            WHERE created_at IS NULL OR created_at >= CURRENT_TIMESTAMP - INTERVAL 14 DAY
            ORDER BY created_at DESC NULLS LAST LIMIT 500
            """
        ).fetchall()
        payload = [list(row) for row in rows]
        now = datetime.now(timezone.utc)
        observation = SourceObservation(
            observation_id=str(uuid4()), run_id=self._run_id, source_id=source_id,
            source_tier=SourceTier.STRUCTURED, url="https://api.sleeper.app/",
            fetched_at=now, observed_at=now, coverage_through=now,
            content_hash=_content_hash(source_id, payload),
            parse_status=ParseStatus.PARSED if rows else ParseStatus.EMPTY,
            evidence_excerpt=f"{len(rows)} recent locally ingested Sleeper transactions",
            payload={"row_count": len(rows), "transactions": payload[:100]}, authoritative=True,
        )
        claims: list[tuple[SourceObservation, ExtractedEventClaim]] = []
        for transaction_id, league_id, kind, status, created_at, adds_raw, drops_raw in rows:
            try:
                adds = json.loads(adds_raw or "{}")
                drops = json.loads(drops_raw or "{}")
            except json.JSONDecodeError:
                continue
            for player_id in sorted(set(adds) | set(drops)):
                row = self._conn.execute(
                    "SELECT full_name, team FROM players WHERE player_id = ?", [player_id]
                ).fetchone()
                claims.append((observation, ExtractedEventClaim(
                    event_type=EventType.ROSTER_TRANSACTION, player_id=str(player_id),
                    player_name=str(row[0]) if row and row[0] else None,
                    team=str(row[1]) if row and row[1] else None,
                    effective_at=created_at or now,
                    expires_at=(created_at.replace(tzinfo=timezone.utc) if created_at else now) + timedelta(days=7),
                    summary=f"{row[0] if row and row[0] else player_id} changed rosters in league {league_id}",
                    details={"transaction_id": transaction_id, "league_id": league_id,
                        "type": kind, "status": status, "added_to": adds.get(str(player_id)),
                        "dropped_by": drops.get(str(player_id))},
                )))
        return SourceBatch(source_id=source_id, domain="transactions", observations=[observation],
            claims=claims, authoritative_empty=not rows, coverage_through=now,
            outcome=SourceOutcome(source_id=source_id, status="complete", records_seen=len(rows),
                observations_written=1, events_written=len(claims)))

    def _market(self) -> SourceBatch:
        source_id = "fantasycalc:market_values"
        rows = self._conn.execute(
            """
            SELECT m.player_id, p.full_name, p.team, m.fantasycalc_value,
                   m.fantasycalc_rank, m.fantasycalc_trend30, m.fetched_at
            FROM market_values m LEFT JOIN players p ON p.player_id = m.player_id
            WHERE m.fantasycalc_trend30 IS NOT NULL
            """
        ).fetchall()
        now = datetime.now(timezone.utc)
        payload = [list(row) for row in rows]
        observation = SourceObservation(
            observation_id=str(uuid4()), run_id=self._run_id, source_id=source_id,
            source_tier=SourceTier.STRUCTURED, url="https://api.fantasycalc.com/",
            fetched_at=now, observed_at=now, coverage_through=now,
            content_hash=_content_hash(source_id, payload),
            parse_status=ParseStatus.PARSED if rows else ParseStatus.EMPTY,
            evidence_excerpt=f"{len(rows)} parsed market rows",
            payload={"row_count": len(rows), "rows": payload[:250]}, authoritative=True,
        )
        claims: list[tuple[SourceObservation, ExtractedEventClaim]] = []
        for player_id, name, team, value, rank, trend, fetched_at in rows:
            delta = float(trend)
            if abs(delta) < 250:
                continue
            claims.append((observation, ExtractedEventClaim(
                event_type=EventType.MARKET_VALUE_CHANGE, player_id=str(player_id),
                player_name=str(name) if name else None, team=str(team) if team else None,
                effective_at=fetched_at or now, expires_at=now + timedelta(days=14),
                summary=f"{name or player_id} market value moved {delta:+.0f}",
                details={"value": value, "rank": rank, "trend_30day": delta},
            )))
        return SourceBatch(source_id=source_id, domain="market", observations=[observation],
            claims=claims, authoritative_empty=False, coverage_through=now,
            outcome=SourceOutcome(
                source_id=source_id,
                status="complete" if rows else "partial",
                records_seen=len(rows),
                observations_written=1,
                events_written=len(claims),
                message=None if rows else "Zero market rows; retained the last confirmed snapshot.",
            ))


__all__ = ["LocalLeagueSource", "NflreadpySource", "PlayerIdentityIndex", "SourceBatch"]

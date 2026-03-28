from __future__ import annotations

import json
from typing import Any

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from fantasy.ingestion.sleeper_mapper import LeagueSettings
from fantasy.routers.deps import get_read_db_conn, get_write_db_conn
from fantasy.trust.scanner import scan_league_format
from fantasy.trust.trust_repo import TrustRepo

router = APIRouter(prefix="/trust", tags=["trust"])


def _load_json(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _load_league_settings(
    conn: duckdb.DuckDBPyConnection, league_id: str
) -> LeagueSettings:
    row = conn.execute(
        """
        SELECT league_id, name, season, scoring_settings, roster_positions,
               settings_blob, superflex, tep, ppr
        FROM leagues
        WHERE league_id = ?
        LIMIT 1
        """,
        [league_id],
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="League not found")
    return LeagueSettings(
        league_id=str(row[0]),
        name=str(row[1]),
        season=str(row[2]),
        scoring_settings=_load_json(row[3], {}),
        roster_positions=_load_json(row[4], []),
        settings_blob=_load_json(row[5], {}),
        superflex=bool(row[6]),
        tep=bool(row[7]),
        ppr=float(row[8]),
    )


def _acknowledgeable_rules(scan) -> list[str]:
    return [
        entry.rule
        for entry in scan.entries
        if entry.support_level == "partially_supported"
        and entry.distorts_recommendations
    ]


def _validated_acknowledgment(repo: TrustRepo, scan):
    acknowledgment = repo.get_acknowledgment(scan.league_id)
    if acknowledgment is None:
        return None
    if set(acknowledgment.acknowledged_rules) != set(_acknowledgeable_rules(scan)):
        repo.clear_acknowledgment(scan.league_id)
        return None
    return acknowledgment


@router.get("/{league_id}/scan")
def get_league_scan(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_read_db_conn),
):
    settings = _load_league_settings(conn, league_id)
    return scan_league_format(settings)


@router.post("/{league_id}/acknowledge")
def acknowledge_league_format(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> dict:
    settings = _load_league_settings(conn, league_id)
    scan = scan_league_format(settings)
    rules = _acknowledgeable_rules(scan)
    if scan.league_unsupported:
        raise HTTPException(
            status_code=400,
            detail="Unsupported league formats cannot be acknowledged away",
        )
    if not rules:
        raise HTTPException(
            status_code=400,
            detail="League has no partially supported rules to acknowledge",
        )
    acknowledgment = TrustRepo(conn).upsert_acknowledgment(league_id, rules)
    return {"league_id": league_id, "acknowledgment": acknowledgment}


@router.get("/{league_id}/acknowledged")
def get_league_acknowledgment(
    league_id: str,
    conn: duckdb.DuckDBPyConnection = Depends(get_write_db_conn),
) -> dict:
    settings = _load_league_settings(conn, league_id)
    scan = scan_league_format(settings)
    acknowledgment = _validated_acknowledgment(TrustRepo(conn), scan)
    return {
        "league_id": league_id,
        "acknowledged": acknowledgment is not None,
        "acknowledgment": acknowledgment,
    }


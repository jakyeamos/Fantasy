from __future__ import annotations

import json
from typing import Any

import duckdb

from fantasy.profiling.models import ManagerProfile, ManagerSummary, PitchAngle


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


class ProfilingRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def _next_id(self, table: str) -> int:
        row = self._conn.execute(
            f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}"
        ).fetchone()
        return int(row[0])

    def upsert_profile(self, profile: ManagerProfile) -> None:
        existing = self._conn.execute(
            """
            SELECT id
            FROM manager_profiles
            WHERE league_id = ? AND roster_id = ?
            """,
            [profile.league_id, profile.roster_id],
        ).fetchone()
        row_id = int(existing[0]) if existing else self._next_id("manager_profiles")
        self._conn.execute(
            """
            INSERT INTO manager_profiles (
                id, league_id, roster_id, evidence_count, low_confidence,
                exploitability_score, exploitation_primary, exploitation_secondary,
                exploitation_evidence, roster_summary, aggregate_trade_stats, trade_history
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (league_id, roster_id) DO UPDATE SET
                evidence_count = EXCLUDED.evidence_count,
                low_confidence = EXCLUDED.low_confidence,
                exploitability_score = EXCLUDED.exploitability_score,
                exploitation_primary = EXCLUDED.exploitation_primary,
                exploitation_secondary = EXCLUDED.exploitation_secondary,
                exploitation_evidence = EXCLUDED.exploitation_evidence,
                roster_summary = EXCLUDED.roster_summary,
                aggregate_trade_stats = EXCLUDED.aggregate_trade_stats,
                trade_history = EXCLUDED.trade_history
            """,
            [
                row_id,
                profile.league_id,
                profile.roster_id,
                profile.evidence_count,
                profile.low_confidence,
                profile.exploitability_score,
                profile.exploitation_primary,
                profile.exploitation_secondary,
                json.dumps(profile.exploitation_evidence, separators=(",", ":")),
                json.dumps(profile.roster_summary or {}, separators=(",", ":")),
                json.dumps(profile.aggregate_trade_stats, separators=(",", ":")),
                json.dumps(profile.trade_history, separators=(",", ":")),
            ],
        )

    def replace_pitch_angles(
        self, league_id: str, roster_id: int, pitch_angles: list[PitchAngle]
    ) -> None:
        self._conn.execute(
            """
            DELETE FROM manager_pitch_angles
            WHERE league_id = ? AND roster_id = ?
            """,
            [league_id, roster_id],
        )
        for angle in sorted(pitch_angles, key=lambda item: item.rank):
            row_id = self._next_id("manager_pitch_angles")
            self._conn.execute(
                """
                INSERT INTO manager_pitch_angles (
                    id, league_id, roster_id, rank, deal_archetype,
                    send_description, avoid_description, reasoning
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    row_id,
                    league_id,
                    roster_id,
                    angle.rank,
                    angle.deal_archetype,
                    angle.send_description,
                    angle.avoid_description,
                    angle.reasoning,
                ],
            )

    def get_pitch_angles(self, league_id: str, roster_id: int) -> list[PitchAngle]:
        rows = self._conn.execute(
            """
            SELECT rank, deal_archetype, send_description, avoid_description, reasoning
            FROM manager_pitch_angles
            WHERE league_id = ? AND roster_id = ?
            ORDER BY rank
            """,
            [league_id, roster_id],
        ).fetchall()
        return [
            PitchAngle(
                rank=int(row[0]),
                deal_archetype=str(row[1]),
                send_description=str(row[2]),
                avoid_description=str(row[3]),
                reasoning=str(row[4]),
            )
            for row in rows
        ]

    def get_profile(self, league_id: str, roster_id: int) -> ManagerProfile | None:
        row = self._conn.execute(
            """
            SELECT mp.league_id, mp.roster_id, CAST(mp.computed_at AS VARCHAR),
                   mp.evidence_count, mp.low_confidence, mp.exploitability_score,
                   mp.exploitation_primary, mp.exploitation_secondary,
                   mp.exploitation_evidence, mp.aggregate_trade_stats,
                   mp.trade_history, mp.roster_summary, r.owner_id, r.owner_display_name, td.primary_label
            FROM manager_profiles mp
            LEFT JOIN rosters r
              ON r.league_id = mp.league_id AND r.roster_id = mp.roster_id
            LEFT JOIN team_directions td
              ON td.league_id = mp.league_id AND td.roster_id = mp.roster_id
            WHERE mp.league_id = ? AND mp.roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        if row is None:
            return None
        return ManagerProfile(
            league_id=str(row[0]),
            roster_id=int(row[1]),
            computed_at=str(row[2]),
            evidence_count=int(row[3]),
            low_confidence=bool(row[4]),
            exploitability_score=float(row[5]),
            exploitation_primary=str(row[6]) if row[6] is not None else None,
            exploitation_secondary=str(row[7]) if row[7] is not None else None,
            exploitation_evidence=_loads(row[8], {}),
            aggregate_trade_stats=_loads(row[9], {}),
            trade_history=_loads(row[10], []),
            roster_summary=_loads(row[11], {}),
            manager_name=str(row[13] or row[12]) if (row[13] or row[12]) is not None else None,
            direction_label=str(row[14]) if row[14] is not None else None,
            pitch_angles=self.get_pitch_angles(league_id, roster_id),
        )

    def list_manager_summaries(self, league_id: str) -> list[ManagerSummary]:
        rows = self._conn.execute(
            """
            SELECT r.roster_id,
                   r.owner_id,
                   r.owner_display_name,
                   td.primary_label,
                   mp.exploitability_score,
                   mp.evidence_count,
                   mp.low_confidence
            FROM rosters r
            LEFT JOIN team_directions td
              ON td.league_id = r.league_id AND td.roster_id = r.roster_id
            LEFT JOIN manager_profiles mp
              ON mp.league_id = r.league_id AND mp.roster_id = r.roster_id
            WHERE r.league_id = ?
            ORDER BY COALESCE(mp.exploitability_score, 0) DESC, r.roster_id
            """,
            [league_id],
        ).fetchall()
        summaries: list[ManagerSummary] = []
        for row in rows:
            roster_id = int(row[0])
            angles = self.get_pitch_angles(league_id, roster_id)
            summaries.append(
                ManagerSummary(
                    league_id=league_id,
                    roster_id=roster_id,
                    manager_name=str(row[2] or row[1] or f"Roster {roster_id}"),
                    direction_label=str(row[3]) if row[3] is not None else None,
                    exploitability_score=float(row[4]) if row[4] is not None else 0.0,
                    evidence_count=int(row[5]) if row[5] is not None else 0,
                    low_confidence=bool(row[6]) if row[6] is not None else True,
                    top_pitch_angle=angles[0] if angles else None,
                )
            )
        return summaries

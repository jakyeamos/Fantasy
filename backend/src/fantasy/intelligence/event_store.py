from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

import duckdb

from fantasy.intelligence.fresh_models import (
    BriefItem,
    EventType,
    ExtractedEventClaim,
    FootballEvent,
    ImpactSummary,
    LeagueImpact,
    MorningBrief,
    ParseStatus,
    SourceObservation,
    SourceOutcome,
    SourceTier,
    VerificationState,
)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _dt(value: datetime | None) -> str:
    return value.astimezone(timezone.utc).isoformat() if value else ""


def _event_fingerprint(claim: ExtractedEventClaim) -> str:
    body = {
        "event_type": claim.event_type.value,
        "player": claim.player_id or (claim.player_name or "").casefold(),
        "team": claim.team,
        "effective_at": _dt(claim.effective_at),
        "details": claim.details,
    }
    return hashlib.sha256(_json(body).encode()).hexdigest()


def _subject_key(claim: ExtractedEventClaim) -> str:
    body = {
        "event_type": claim.event_type.value,
        "player": claim.player_id or (claim.player_name or "").casefold(),
        "team": claim.team,
        "effective_date": claim.effective_at.date().isoformat() if claim.effective_at else None,
    }
    return hashlib.sha256(_json(body).encode()).hexdigest()


class IntelligenceStore:
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def start_run(self, trigger: str) -> str:
        run_id = str(uuid4())
        self._conn.execute(
            "INSERT INTO intelligence_source_runs (run_id, trigger, status) VALUES (?, ?, 'running')",
            [run_id, trigger],
        )
        return run_id

    def finish_run(
        self,
        run_id: str,
        *,
        status: str,
        outcomes: list[SourceOutcome],
        event_count: int,
        impact_count: int,
        brief_id: str | None,
        error_message: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            UPDATE intelligence_source_runs
            SET status = ?, completed_at = CURRENT_TIMESTAMP, source_outcomes_json = ?,
                event_count = ?, impact_count = ?, brief_id = ?, error_message = ?
            WHERE run_id = ?
            """,
            [
                status,
                _json([item.model_dump(mode="json") for item in outcomes]),
                event_count,
                impact_count,
                brief_id,
                error_message,
                run_id,
            ],
        )

    def save_observation(self, observation: SourceObservation) -> SourceObservation:
        existing = self._conn.execute(
            """
            SELECT observation_id FROM source_observations
            WHERE source_id = ? AND content_hash = ?
            """,
            [observation.source_id, observation.content_hash],
        ).fetchone()
        if existing:
            return self.get_observation(str(existing[0]))
        self._conn.execute(
            """
            INSERT INTO source_observations (
                observation_id, run_id, source_id, source_tier, url, fetched_at,
                observed_at, effective_at, coverage_through, content_hash, parse_status,
                evidence_excerpt, payload_json, authoritative, model_extracted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                observation.observation_id,
                observation.run_id,
                observation.source_id,
                observation.source_tier.value,
                observation.url,
                observation.fetched_at,
                observation.observed_at,
                observation.effective_at,
                observation.coverage_through,
                observation.content_hash,
                observation.parse_status.value,
                observation.evidence_excerpt,
                _json(observation.payload),
                observation.authoritative,
                observation.model_extracted,
            ],
        )
        return observation

    def find_observation(
        self, source_id: str, content_hash: str
    ) -> SourceObservation | None:
        row = self._conn.execute(
            """
            SELECT observation_id FROM source_observations
            WHERE source_id = ? AND content_hash = ?
            """,
            [source_id, content_hash],
        ).fetchone()
        return self.get_observation(str(row[0])) if row else None

    def list_events_for_observation(self, observation_id: str) -> list[FootballEvent]:
        rows = self._conn.execute(
            """
            SELECT event_id FROM event_evidence
            WHERE observation_id = ? ORDER BY linked_at, event_id
            """,
            [observation_id],
        ).fetchall()
        return [self.get_event(str(row[0])) for row in rows]

    def get_observation(self, observation_id: str) -> SourceObservation:
        row = self._conn.execute(
            """
            SELECT observation_id, run_id, source_id, source_tier, url, fetched_at,
                   observed_at, effective_at, coverage_through, content_hash, parse_status,
                   evidence_excerpt, payload_json, authoritative, model_extracted
            FROM source_observations WHERE observation_id = ?
            """,
            [observation_id],
        ).fetchone()
        if not row:
            raise KeyError(observation_id)
        return SourceObservation(
            observation_id=str(row[0]), run_id=str(row[1]), source_id=str(row[2]),
            source_tier=SourceTier(str(row[3])), url=row[4], fetched_at=row[5],
            observed_at=row[6], effective_at=row[7], coverage_through=row[8],
            content_hash=str(row[9]), parse_status=ParseStatus(str(row[10])),
            evidence_excerpt=row[11], payload=json.loads(row[12] or "{}"),
            authoritative=bool(row[13]), model_extracted=bool(row[14]),
        )

    def upsert_claim(
        self, observation: SourceObservation, claim: ExtractedEventClaim
    ) -> FootballEvent:
        fingerprint = _event_fingerprint(claim)
        subject_key = _subject_key(claim)
        row = self._conn.execute(
            "SELECT event_id FROM football_events WHERE fingerprint = ?",
            [fingerprint],
        ).fetchone()
        event_id = str(row[0]) if row else str(uuid4())
        if not row:
            initial_state = self._initial_state(observation, claim)
            self._conn.execute(
                """
                INSERT INTO football_events (
                    event_id, fingerprint, subject_key, event_type, player_id, player_name,
                    team, effective_at, observed_at, expires_at, verification_state,
                    confidence, summary, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [event_id, fingerprint, subject_key, claim.event_type.value, claim.player_id,
                 claim.player_name, claim.team, claim.effective_at,
                 observation.observed_at or observation.fetched_at, claim.expires_at,
                 initial_state.value, self._confidence(initial_state), claim.summary,
                 _json(claim.details)],
            )
        self._conn.execute(
            """
            INSERT INTO event_evidence (event_id, observation_id) VALUES (?, ?)
            ON CONFLICT (event_id, observation_id) DO NOTHING
            """,
            [event_id, observation.observation_id],
        )
        self._reconcile_subject(subject_key)
        return self.get_event(event_id)

    @staticmethod
    def _initial_state(
        observation: SourceObservation, claim: ExtractedEventClaim
    ) -> VerificationState:
        if not claim.player_id:
            return VerificationState.MANUAL_REVIEW
        if observation.authoritative and not observation.model_extracted:
            return VerificationState.CONFIRMED
        return VerificationState.WATCH

    @staticmethod
    def _confidence(state: VerificationState) -> float:
        return {
            VerificationState.CONFIRMED: 0.95,
            VerificationState.WATCH: 0.55,
            VerificationState.CONFLICTED: 0.35,
            VerificationState.EXPIRED: 0.0,
            VerificationState.MANUAL_REVIEW: 0.25,
        }[state]

    def _reconcile_subject(self, subject_key: str) -> None:
        rows = self._conn.execute(
            """
            SELECT e.event_id, e.fingerprint, e.expires_at, e.player_id,
                   COUNT(DISTINCT o.source_id) AS source_count,
                   MAX(CASE WHEN o.authoritative AND NOT o.model_extracted THEN 1 ELSE 0 END)
            FROM football_events e
            JOIN event_evidence ee ON ee.event_id = e.event_id
            JOIN source_observations o ON o.observation_id = ee.observation_id
            WHERE e.subject_key = ?
            GROUP BY e.event_id, e.fingerprint, e.expires_at, e.player_id
            """,
            [subject_key],
        ).fetchall()
        fingerprints = {str(row[1]) for row in rows}
        conflict = len(fingerprints) > 1
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for event_id, _fingerprint, expires_at, player_id, source_count, has_authoritative in rows:
            if expires_at is not None and expires_at < now:
                state = VerificationState.EXPIRED
            elif not player_id:
                state = VerificationState.MANUAL_REVIEW
            elif conflict:
                state = VerificationState.CONFLICTED
            elif bool(has_authoritative) or int(source_count) >= 2:
                state = VerificationState.CONFIRMED
            else:
                current = self._conn.execute(
                    "SELECT verification_state FROM football_events WHERE event_id = ?",
                    [event_id],
                ).fetchone()
                state = VerificationState(str(current[0]))
            self._conn.execute(
                """
                UPDATE football_events SET verification_state = ?, confidence = ?,
                    updated_at = CURRENT_TIMESTAMP WHERE event_id = ?
                """,
                [state.value, self._confidence(state), event_id],
            )

    def get_event(self, event_id: str) -> FootballEvent:
        row = self._conn.execute(
            """
            SELECT event_id, fingerprint, subject_key, event_type, player_id, player_name,
                   team, effective_at, observed_at, expires_at, verification_state,
                   confidence, summary, details_json
            FROM football_events WHERE event_id = ?
            """,
            [event_id],
        ).fetchone()
        if not row:
            raise KeyError(event_id)
        evidence = self._conn.execute(
            "SELECT observation_id FROM event_evidence WHERE event_id = ? ORDER BY linked_at",
            [event_id],
        ).fetchall()
        return FootballEvent(
            event_id=str(row[0]), fingerprint=str(row[1]), subject_key=str(row[2]),
            event_type=EventType(str(row[3])), player_id=row[4], player_name=row[5], team=row[6],
            effective_at=row[7], observed_at=row[8], expires_at=row[9],
            verification_state=VerificationState(str(row[10])), confidence=float(row[11]),
            summary=str(row[12]), details=json.loads(row[13] or "{}"),
            observation_ids=[str(item[0]) for item in evidence],
        )

    def list_events(self, *, states: list[VerificationState] | None = None) -> list[FootballEvent]:
        query = "SELECT event_id FROM football_events"
        params: list[Any] = []
        if states:
            query += " WHERE verification_state IN (SELECT UNNEST(?))"
            params.append([state.value for state in states])
        query += " ORDER BY effective_at DESC NULLS LAST, observed_at DESC"
        return [self.get_event(str(row[0])) for row in self._conn.execute(query, params).fetchall()]

    def review_event(self, event_id: str, decision: str, notes: str | None) -> FootballEvent:
        self.get_event(event_id)
        review_id = str(uuid4())
        state = VerificationState.CONFIRMED if decision == "confirm" else VerificationState.EXPIRED
        self._conn.execute(
            "INSERT INTO event_reviews (review_id, event_id, decision, notes) VALUES (?, ?, ?, ?)",
            [review_id, event_id, decision, notes],
        )
        self._conn.execute(
            "UPDATE football_events SET verification_state = ?, confidence = ?, updated_at = CURRENT_TIMESTAMP WHERE event_id = ?",
            [state.value, self._confidence(state), event_id],
        )
        return self.get_event(event_id)

    def replace_impacts(self, event_id: str, impacts: list[LeagueImpact]) -> None:
        self._conn.execute("DELETE FROM league_impacts WHERE event_id = ?", [event_id])
        for impact in impacts:
            summary = impact.impact_summary
            self._conn.execute(
                """
                INSERT INTO league_impacts (
                    impact_id, event_id, league_id, roster_id, impact_type,
                    affected_asset_ids_json, headline, explanation, before_json,
                    after_json, deltas_json, confidence, actionable, recommended_action,
                    cta_label, cta_destination, invalidation, model_version, computed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [impact.impact_id, impact.event_id, impact.league_id, impact.roster_id,
                 impact.impact_type, _json(summary.affected_asset_ids), impact.headline,
                 impact.explanation, _json(summary.before), _json(summary.after),
                 _json(summary.deltas), impact.confidence, impact.actionable,
                 impact.recommended_action, impact.cta_label, impact.cta_destination,
                 impact.invalidation, impact.model_version, impact.computed_at],
            )

    def list_impacts(self, event_id: str | None = None) -> list[LeagueImpact]:
        query = """
            SELECT impact_id, event_id, league_id, roster_id, impact_type,
                   affected_asset_ids_json, headline, explanation, before_json,
                   after_json, deltas_json, confidence, actionable, recommended_action,
                   cta_label, cta_destination, invalidation, model_version, computed_at
            FROM league_impacts
        """
        params: list[Any] = []
        if event_id:
            query += " WHERE event_id = ?"
            params.append(event_id)
        query += " ORDER BY actionable DESC, confidence DESC, computed_at DESC"
        result: list[LeagueImpact] = []
        for row in self._conn.execute(query, params).fetchall():
            result.append(LeagueImpact(
                impact_id=str(row[0]), event_id=str(row[1]), league_id=str(row[2]),
                roster_id=int(row[3]) if row[3] is not None else None, impact_type=str(row[4]),
                impact_summary=ImpactSummary(affected_asset_ids=json.loads(row[5] or "[]"),
                    before=json.loads(row[8] or "{}"), after=json.loads(row[9] or "{}"),
                    deltas=json.loads(row[10] or "{}")), headline=str(row[6]),
                explanation=str(row[7]), confidence=float(row[11]), actionable=bool(row[12]),
                recommended_action=row[13], cta_label=row[14], cta_destination=row[15],
                invalidation=str(row[16]), model_version=str(row[17]), computed_at=row[18],
            ))
        return result

    def publish_brief(
        self, *, run_id: str, status: str, items: list[BriefItem], outcomes: list[SourceOutcome]
    ) -> MorningBrief:
        today = date.today()
        content_hash = hashlib.sha256(_json({
            "status": status,
            "source_health": [outcome.model_dump(mode="json") for outcome in outcomes],
            "items": [item.model_dump(mode="json", exclude={"item_id"}) for item in items],
        }).encode()).hexdigest()
        existing = self._conn.execute(
            "SELECT brief_id FROM daily_briefs WHERE brief_date = ? AND content_hash = ?",
            [today, content_hash],
        ).fetchone()
        if existing:
            return self._get_brief_by_id(str(existing[0]))
        brief_id = str(uuid4())
        self._conn.execute(
            """
            INSERT INTO daily_briefs (
                brief_id, brief_date, content_hash, run_id, status,
                source_health_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [brief_id, today, content_hash, run_id, status,
             _json([o.model_dump(mode="json") for o in outcomes]),
             datetime.now(timezone.utc).replace(tzinfo=None)],
        )
        for item in items:
            self._conn.execute(
                """
                INSERT INTO daily_brief_items (
                    item_id, brief_id, event_id, league_id, roster_id, lane, priority_rank,
                    headline, why_it_matters, recommended_action, confidence, source_summary,
                    invalidation, impact_json, cta_label, cta_destination
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [item.item_id, brief_id, item.event_id, item.league_id, item.roster_id,
                 item.lane, item.priority_rank, item.headline, item.why_it_matters,
                 item.recommended_action, item.confidence, item.source_summary,
                 item.invalidation, _json(item.impact_summary.model_dump()),
                 item.cta_label, item.cta_destination],
            )
        return self._get_brief_by_id(brief_id)

    def get_brief(self, brief_date: date) -> MorningBrief:
        row = self._conn.execute(
            """
            SELECT brief_id FROM daily_briefs WHERE brief_date = ?
            ORDER BY created_at DESC, brief_id DESC LIMIT 1
            """,
            [brief_date],
        ).fetchone()
        if not row:
            raise KeyError(brief_date.isoformat())
        return self._get_brief_by_id(str(row[0]))

    def _get_brief_by_id(self, brief_id: str) -> MorningBrief:
        row = self._conn.execute(
            """
            SELECT brief_id, brief_date, run_id, status, source_health_json, created_at
            FROM daily_briefs WHERE brief_id = ?
            """,
            [brief_id],
        ).fetchone()
        if not row:
            raise KeyError(brief_id)
        item_rows = self._conn.execute(
            """
            SELECT item_id, event_id, league_id, roster_id, lane, priority_rank,
                   headline, why_it_matters, recommended_action, confidence, source_summary,
                   invalidation, impact_json, cta_label, cta_destination
            FROM daily_brief_items WHERE brief_id = ? ORDER BY priority_rank, item_id
            """,
            [brief_id],
        ).fetchall()
        items = [BriefItem(
            item_id=str(i[0]), event_id=str(i[1]), league_id=i[2],
            roster_id=int(i[3]) if i[3] is not None else None, lane=str(i[4]),
            priority_rank=int(i[5]), headline=str(i[6]), why_it_matters=str(i[7]),
            recommended_action=i[8], confidence=float(i[9]), source_summary=str(i[10]),
            invalidation=str(i[11]), impact_summary=ImpactSummary(**json.loads(i[12] or "{}")),
            cta_label=i[13], cta_destination=i[14],
        ) for i in item_rows]
        return MorningBrief(
            brief_id=str(row[0]), brief_date=row[1], run_id=str(row[2]), status=str(row[3]),
            source_health=[SourceOutcome(**item) for item in json.loads(row[4] or "[]")],
            created_at=row[5], items=items,
        )

    def save_feedback(self, brief_id: str, item_id: str, verdict: str, notes: str | None) -> str:
        feedback_id = str(uuid4())
        self._conn.execute(
            "INSERT INTO brief_feedback (feedback_id, brief_id, item_id, verdict, notes) VALUES (?, ?, ?, ?, ?)",
            [feedback_id, brief_id, item_id, verdict, notes],
        )
        return feedback_id


__all__ = ["IntelligenceStore"]

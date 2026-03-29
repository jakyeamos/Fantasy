from __future__ import annotations

from datetime import datetime, timezone

from fantasy.context.calendar_service import CalendarService
from fantasy.context.constants import CALENDAR_GUIDANCE
from fantasy.context.context_repo import ContextRepo


def test_auto_detect_calendar_states(db) -> None:
    service = CalendarService(
        repo=ContextRepo(db),
        now=lambda: datetime(2026, 4, 24, tzinfo=timezone.utc),
    )
    assert service.active_state("league_x") == "post_nfl_draft"

    service = CalendarService(
        repo=ContextRepo(db),
        now=lambda: datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    assert service.active_state("league_x") == "post_combine"


def test_manual_override_beats_auto_detection(db) -> None:
    repo = ContextRepo(db)
    repo.upsert_override("league_x", "startup")

    service = CalendarService(
        repo=repo,
        now=lambda: datetime(2026, 9, 15, tzinfo=timezone.utc),
    )

    context = service.get_context("league_x")
    assert context.active_state == "startup"
    assert context.is_override is True
    assert context.override_set_by == "user"


def test_calendar_guidance_varies_by_state() -> None:
    rookie_fever = CALENDAR_GUIDANCE.get(("rookie_fever", "pick_sell"))
    early_season = CALENDAR_GUIDANCE.get(("early_season", "pick_buy"))

    assert rookie_fever
    assert early_season
    assert rookie_fever != early_season

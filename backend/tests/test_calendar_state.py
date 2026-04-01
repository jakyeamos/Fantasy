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


def test_persisted_override_is_ignored_for_calendar_truth(db) -> None:
    db.execute(
        """
        INSERT INTO calendar_overrides (id, league_id, state, set_by, set_at, expires_at)
        VALUES (1, 'league_x', 'startup', 'user', CURRENT_TIMESTAMP, NULL)
        """
    )
    service = CalendarService(
        repo=ContextRepo(db),
        now=lambda: datetime(2026, 9, 15, tzinfo=timezone.utc),
    )

    context = service.get_context("league_x")
    assert context.active_state == "early_season"


def test_calendar_guidance_varies_by_state() -> None:
    rookie_fever = CALENDAR_GUIDANCE.get(("rookie_fever", "pick_sell"))
    early_season = CALENDAR_GUIDANCE.get(("early_season", "pick_buy"))

    assert rookie_fever
    assert early_season
    assert rookie_fever != early_season

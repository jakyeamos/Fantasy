from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from fantasy.context.constants import CALENDAR_WINDOWS, FALLBACK_STATE
from fantasy.context.context_repo import ContextRepo
from fantasy.context.models import CalendarContext

ClockFn = Callable[[], datetime]


def _in_range(m: int, d: int, sm: int, sd: int, em: int, ed: int) -> bool:
    if sm <= em:
        if sm < m < em:
            return True
        if m == sm and d >= sd:
            return True
        if m == em and d <= ed:
            return True
    else:
        if m > sm or (m == sm and d >= sd):
            return True
        if m < em or (m == em and d <= ed):
            return True
    return False


def _detect_state(now: datetime) -> str:
    month, day = now.month, now.day
    for start_m, start_d, end_m, end_d, state in CALENDAR_WINDOWS:
        if _in_range(month, day, start_m, start_d, end_m, end_d):
            return state
    return FALLBACK_STATE


class CalendarService:
    def __init__(
        self,
        repo: ContextRepo,
        now: ClockFn = lambda: datetime.now(tz=timezone.utc),
    ) -> None:
        self._repo = repo
        self._now = now

    def active_state(self, _league_id: str) -> str:
        return _detect_state(self._now())

    def get_context(self, _league_id: str) -> CalendarContext:
        return CalendarContext(
            active_state=_detect_state(self._now()),
            detected_at=self._now(),
        )

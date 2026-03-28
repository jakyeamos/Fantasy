from __future__ import annotations

from fantasy.trust.constants import (
    TRUST_MODIFIER_FULL_SUPPORT,
    TRUST_MODIFIER_PARTIAL_SUPPORT,
    TRUST_MODIFIER_UNSUPPORTED,
)
from fantasy.trust.models import LeagueFormatScan


def compute_trust_modifier(scan: LeagueFormatScan, acknowledged: bool) -> float:
    if scan.league_unsupported:
        return TRUST_MODIFIER_UNSUPPORTED
    if scan.needs_acknowledgment and not acknowledged:
        return TRUST_MODIFIER_PARTIAL_SUPPORT
    if scan.needs_acknowledgment and acknowledged:
        return TRUST_MODIFIER_PARTIAL_SUPPORT
    return TRUST_MODIFIER_FULL_SUPPORT


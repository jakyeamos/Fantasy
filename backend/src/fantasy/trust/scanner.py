from __future__ import annotations

from fantasy.ingestion.sleeper_mapper import LeagueSettings
from fantasy.trust.constants import FormatRule, RULE_SUPPORT_MATRIX
from fantasy.trust.models import LeagueFormatScan, RuleScanEntry

IDP_POSITION_STRINGS: frozenset[str] = frozenset(
    {"DL", "LB", "DB", "IDP_FLEX", "EDGE", "CB", "S"}
)


def scan_league_format(settings: LeagueSettings) -> LeagueFormatScan:
    settings_blob = settings.settings_blob
    scoring_settings = settings.scoring_settings
    roster_positions = set(settings.roster_positions)
    detected: list[FormatRule] = []

    if settings_blob.get("type", 2) != 2:
        detected.append(FormatRule.NON_DYNASTY)

    if settings.ppr >= 1.0:
        detected.append(FormatRule.FULL_PPR)
    elif settings.ppr >= 0.5:
        detected.append(FormatRule.HALF_PPR)
    else:
        detected.append(FormatRule.STANDARD)

    if settings.superflex:
        detected.append(FormatRule.SUPERFLEX)
    if settings.tep:
        detected.append(FormatRule.TEP)

    if settings_blob.get("league_average_match", 0):
        detected.append(FormatRule.MEDIAN_WINS)
    if settings_blob.get("best_ball", 0):
        detected.append(FormatRule.BEST_BALL)
    if settings_blob.get("salary_cap", 0):
        detected.append(FormatRule.SALARY_CAP)
    if roster_positions & IDP_POSITION_STRINGS:
        detected.append(FormatRule.IDP)
    if (
        scoring_settings.get("rush_fd", 0.0)
        or scoring_settings.get("rec_fd", 0.0)
        or scoring_settings.get("pass_fd", 0.0)
    ):
        detected.append(FormatRule.FIRST_DOWN_SCORING)
    if (
        scoring_settings.get("ret_yd", 0.0)
        or scoring_settings.get("kr_td", 0.0)
        or scoring_settings.get("pr_td", 0.0)
    ):
        detected.append(FormatRule.RETURN_SCORING)
    if scoring_settings.get("bonus_rec_wr", 0.0):
        detected.append(FormatRule.WR_BONUS)

    entries = [
        RuleScanEntry(
            rule=str(rule),
            support_level=RULE_SUPPORT_MATRIX[rule][0],
            reason=RULE_SUPPORT_MATRIX[rule][1],
            distorts_recommendations=RULE_SUPPORT_MATRIX[rule][2],
        )
        for rule in detected
    ]
    needs_acknowledgment = any(
        entry.support_level == "partially_supported"
        and entry.distorts_recommendations
        for entry in entries
    )
    league_unsupported = any(
        entry.support_level == "unsupported" for entry in entries
    )
    return LeagueFormatScan(
        league_id=settings.league_id,
        entries=entries,
        needs_acknowledgment=needs_acknowledgment,
        league_unsupported=league_unsupported,
    )


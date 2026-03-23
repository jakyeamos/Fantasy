from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class LeagueSettings(BaseModel):
    league_id: str
    name: str
    season: str
    scoring_settings: dict[str, float]
    roster_positions: list[str]
    settings_blob: dict[str, Any]
    superflex: bool
    tep: bool
    ppr: float


class RosterSnapshot(BaseModel):
    roster_id: int
    owner_id: str | None = None
    owner_display_name: str | None = None
    league_id: str
    starters: list[str]
    bench: list[str]
    ir: list[str]
    taxi: list[str]


class TradedPick(BaseModel):
    league_id: str
    season: str
    round: int
    roster_id: int
    owner_id: int
    previous_owner_id: int | None = None


class DraftSlot(BaseModel):
    league_id: str
    draft_id: str
    season: int
    roster_id: int
    confirmed_slot: int
    status: str


class StandingRow(BaseModel):
    league_id: str
    roster_id: int
    wins: int = 0
    losses: int = 0
    ties: int = 0
    fpts: float = 0.0
    fpts_against: float = 0.0


class TransactionRecord(BaseModel):
    transaction_id: str
    league_id: str
    type: str
    status: str
    created_at: datetime | None = None
    roster_ids: list[int]
    adds: dict[str, int]
    drops: dict[str, int]
    draft_picks: list[dict[str, Any]]
    week: int

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SleeperMapper:
    @staticmethod
    def map_league(raw: dict[str, Any]) -> LeagueSettings:
        scoring_settings = raw.get("scoring_settings") or {}
        roster_positions = raw.get("roster_positions") or []

        payload = {
            "league_id": raw.get("league_id"),
            "name": raw.get("name"),
            "season": raw.get("season"),
            "scoring_settings": {
                key: float(value) for key, value in scoring_settings.items() if value is not None
            },
            "roster_positions": [str(pos) for pos in roster_positions],
            "settings_blob": raw.get("settings") or {},
            "superflex": "SUPER_FLEX" in roster_positions,
            "tep": float(scoring_settings.get("bonus_rec_te", 0.0) or 0.0) > 0.0,
            "ppr": float(scoring_settings.get("rec", 0.0) or 0.0),
        }
        return LeagueSettings.model_validate(payload)

    @staticmethod
    def map_roster(raw: dict[str, Any]) -> RosterSnapshot:
        def _valid_player_ids(values: list[Any] | None) -> list[str]:
            return [
                str(player)
                for player in (values or [])
                if player not in (None, "", 0, "0")
            ]

        starters = _valid_player_ids(raw.get("starters"))
        players = _valid_player_ids(raw.get("players"))
        reserve = _valid_player_ids(raw.get("reserve"))
        taxi = _valid_player_ids(raw.get("taxi"))

        excluded = set(starters) | set(reserve) | set(taxi)
        bench = [player for player in players if player not in excluded]

        payload = {
            "roster_id": raw.get("roster_id"),
            "owner_id": raw.get("owner_id"),
            "owner_display_name": raw.get("owner_display_name"),
            "league_id": raw.get("league_id"),
            "starters": starters,
            "bench": bench,
            "ir": reserve,
            "taxi": taxi,
        }
        return RosterSnapshot.model_validate(payload)

    @staticmethod
    def map_traded_picks(raw: list[dict[str, Any]], league_id: str) -> list[TradedPick]:
        return [
            TradedPick.model_validate(
                {
                    "league_id": item.get("league_id") or league_id,
                    "season": item.get("season"),
                    "round": item.get("round"),
                    "roster_id": item.get("roster_id"),
                    "owner_id": item.get("owner_id"),
                    "previous_owner_id": item.get("previous_owner_id"),
                }
            )
            for item in (raw or [])
        ]

    @staticmethod
    def map_draft_slots(raw: list[dict[str, Any]], league_id: str) -> list[DraftSlot]:
        slots: list[DraftSlot] = []
        for draft in raw or []:
            draft_id = draft.get("draft_id")
            season = draft.get("season")
            status = str(draft.get("status") or "pre_draft")
            slot_to_roster = draft.get("slot_to_roster_id") or {}
            if not draft_id or not season or not slot_to_roster:
                continue
            for slot_str, roster_id in slot_to_roster.items():
                try:
                    slots.append(
                        DraftSlot(
                            league_id=league_id,
                            draft_id=str(draft_id),
                            season=int(season),
                            roster_id=int(roster_id),
                            confirmed_slot=int(slot_str),
                            status=status,
                        )
                    )
                except (ValueError, TypeError):
                    continue
        return slots

    @staticmethod
    def map_standing(raw: dict[str, Any], league_id: str) -> StandingRow:
        settings = raw.get("settings") or {}
        fpts_whole = float(settings.get("fpts", 0) or 0)
        fpts_decimal = float(settings.get("fpts_decimal", 0) or 0)
        fpts_value = fpts_whole + (fpts_decimal / 100.0)

        payload = {
            "league_id": league_id,
            "roster_id": raw.get("roster_id"),
            "wins": int(settings.get("wins", 0) or 0),
            "losses": int(settings.get("losses", 0) or 0),
            "ties": int(settings.get("ties", 0) or 0),
            "fpts": fpts_value,
            "fpts_against": float(settings.get("fpts_against", 0) or 0),
        }
        return StandingRow.model_validate(payload)

    @staticmethod
    def map_transactions(raw: list[dict[str, Any]], league_id: str) -> list[TransactionRecord]:
        mapped: list[TransactionRecord] = []
        for item in raw or []:
            created_ms = item.get("created")
            created_at = (
                datetime.fromtimestamp(float(created_ms) / 1000.0) if created_ms is not None else None
            )
            payload = {
                "transaction_id": item.get("transaction_id"),
                "league_id": league_id,
                "type": item.get("type"),
                "status": item.get("status", "unknown"),
                "created_at": created_at,
                "roster_ids": [int(roster_id) for roster_id in (item.get("roster_ids") or [])],
                "adds": {
                    str(player_id): int(roster_id)
                    for player_id, roster_id in (item.get("adds") or {}).items()
                },
                "drops": {
                    str(player_id): int(roster_id)
                    for player_id, roster_id in (item.get("drops") or {}).items()
                },
                "draft_picks": list(item.get("draft_picks") or []),
                "week": int(item.get("leg", 0) or 0),
            }
            mapped.append(TransactionRecord.model_validate(payload))
        return mapped


__all__ = [
    "LeagueSettings",
    "RosterSnapshot",
    "TradedPick",
    "StandingRow",
    "TransactionRecord",
    "SleeperMapper",
]

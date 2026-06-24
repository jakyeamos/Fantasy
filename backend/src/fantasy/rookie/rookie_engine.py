from __future__ import annotations

from datetime import datetime, timezone

import duckdb

from fantasy.rookie.constants import (
    ARCHETYPE_FALLBACK_TEMPLATE,
    ARCHETYPE_LABELS,
    BASELINE_TIER1_COUNT,
    BASELINE_TIER2_COUNT,
    CLASS_TIER1_WEIGHT,
    CLASS_TIER2_WEIGHT,
    CLASS_WEAKNESS_THRESHOLD,
    EARLY_PICK_VALUE_THRESHOLD,
    GAP_THRESHOLD,
    MAX_TIER_COUNT,
    POSITIONAL_RUN_THRESHOLD,
    RISK_BAND_HIGH,
    RISK_BAND_LOW,
    RISK_BAND_MODERATE,
    SLOT_AVAILABILITY_MAX_SLOT_MULTIPLIER,
    SLOT_AVAILABILITY_SLOPE,
    STRONG_TIER2_THRESHOLD,
    TENDENCY_MIN_SAMPLE_SIZE,
    TIER_LABELS,
    VALUE_GAP_THRESHOLD,
)
from fantasy.rookie.models import (
    DraftRoomResult,
    RookieBoardResult,
    RookiePlayer,
    RookieTier,
    TendencyWarning,
    TradeVerdict,
)
from fantasy.rookie.rookie_repo import RookieRepo
from fantasy.recommendation.card_engine import RecommendationCardEngine


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _scale_higher(value: object, low: float, high: float) -> float:
    numeric = _as_float(value)
    if numeric is None:
        return 50.0
    return _clamp(((numeric - low) / max(high - low, 0.01)) * 100.0)


def _scale_lower(value: object, low: float, high: float) -> float:
    numeric = _as_float(value)
    if numeric is None:
        return 50.0
    return _clamp(((high - numeric) / max(high - low, 0.01)) * 100.0)


def slot_availability_probability(rank: int, slot: int) -> float:
    if slot < rank:
        return 0.05
    gap = slot - rank
    return min(0.95, 0.50 + gap * SLOT_AVAILABILITY_SLOPE)


class RookieEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn
        self._repo = RookieRepo(conn)
        self._card_engine = RecommendationCardEngine(conn)

    def compute_board(self, league_id: str) -> RookieBoardResult:
        league_settings = self._repo.get_league_settings(league_id)
        raw_players = self._repo.get_available_rookies(league_id)
        computed_at = datetime.now(timezone.utc)

        if not raw_players:
            board = RookieBoardResult(
                league_id=league_id,
                league_format=self._format_label(league_settings),
                class_strength_signal=0.0,
                tiers=[],
                computed_at=computed_at,
            )
            self._repo.save_board_cache(league_id, 0.0, board.model_dump_json())
            self._repo.replace_league_tendencies(league_id, [])
            return board

        adp_sorted = sorted(raw_players, key=lambda player: (float(player.get("adp", 999.0)), player["full_name"]))
        adp_rank_by_player = {
            player["player_id"]: index + 1 for index, player in enumerate(adp_sorted)
        }
        max_slot = max(
            int(league_settings.get("league_size", 12)) * SLOT_AVAILABILITY_MAX_SLOT_MULTIPLIER,
            len(raw_players),
        )

        scored_rows: list[dict[str, object]] = []
        for raw_player in raw_players:
            scored_rows.append(
                {
                    "raw": raw_player,
                    "player": RookiePlayer(
                        player_id=str(raw_player["player_id"]),
                        full_name=str(raw_player["full_name"]),
                        position=str(raw_player["position"]),
                        archetype_label=self._assign_archetype(raw_player),
                        risk_band=self._assign_risk_band(raw_player),
                        composite_score=round(self._score_rookie(raw_player, league_settings), 2),
                        tier_number=1,
                        available_probability_by_slot={},
                        model_vs_market_gap=self._card_engine.model_vs_market_gap(
                            league_id,
                            str(raw_player["player_id"]),
                        ),
                    ),
                    "adp_rank": adp_rank_by_player[str(raw_player["player_id"])],
                }
            )

        scored_rows.sort(
            key=lambda row: (
                -float(row["player"].composite_score),  # type: ignore[attr-defined]
                int(row["adp_rank"]),
                str(row["player"].full_name),  # type: ignore[attr-defined]
            )
        )

        for system_rank, row in enumerate(scored_rows, start=1):
            player = row["player"]  # type: ignore[assignment]
            player.available_probability_by_slot = {
                self._format_slot(slot, league_size=int(league_settings["league_size"])): round(
                    slot_availability_probability(system_rank, slot), 2
                )
                for slot in range(1, max_slot + 1)
            }
            row["system_rank"] = system_rank

        tiers = self._assign_tiers([row["player"] for row in scored_rows])  # type: ignore[list-item]
        player_by_id = {
            player.player_id: player
            for tier in tiers
            for player in tier.players
        }
        for row in scored_rows:
            row["player"] = player_by_id[row["player"].player_id]  # type: ignore[index]

        class_strength_signal = self._compute_class_strength(
            [row["player"] for row in scored_rows]  # type: ignore[list-item]
        )
        board = RookieBoardResult(
            league_id=league_id,
            league_format=self._format_label(league_settings),
            class_strength_signal=class_strength_signal,
            tiers=tiers,
            computed_at=computed_at,
        )
        self._repo.save_board_cache(league_id, class_strength_signal, board.model_dump_json())
        self._repo.replace_league_tendencies(
            league_id,
            self._build_tendencies(scored_rows),
        )
        return board

    def compute_class_strength(self, league_id: str) -> float:
        return self.compute_board(league_id).class_strength_signal

    def compute_draft_room(self, league_id: str, pick_slot: int) -> DraftRoomResult:
        league_settings = self._repo.get_league_settings(league_id)
        board = self.compute_board(league_id)
        tendencies = self._repo.get_league_tendencies(league_id)
        available = self._estimate_available_at_slot(
            board,
            pick_slot,
            league_size=int(league_settings["league_size"]),
        )
        best_in_abstract = next(
            (
                player
                for tier in board.tiers
                for player in tier.players
            ),
            None,
        )
        return DraftRoomResult(
            league_id=league_id,
            pick_slot=pick_slot,
            pick_slot_display=self._format_slot(
                pick_slot, league_size=int(league_settings["league_size"])
            ),
            trade_verdict=self._compute_trade_verdict(pick_slot, board, available[0] if available else None),
            best_in_abstract=best_in_abstract,
            tendency_warnings=self._build_tendency_warnings(
                tendencies,
                available,
                pick_slot,
                league_size=int(league_settings["league_size"]),
            ),
        )

    def _score_rookie(self, player: dict, league_settings: dict) -> float:
        adp = float(player.get("adp", 999.0))
        metadata = player.get("metadata", {})
        position = str(player.get("position", ""))

        model_score = {
            "hit": 92.0,
            "mediocre": 62.0,
            "bust": 34.0,
        }.get(str(metadata.get("predicted_bucket") or "").lower(), 55.0)
        predicted_tier = int(metadata.get("predicted_tier") or 5)
        model_score = (model_score * 0.75) + (_clamp(110.0 - predicted_tier * 18.0) * 0.25)

        draft_score = _scale_lower(metadata.get("draft_ovr") or metadata.get("draft_pick"), 1.0, 160.0)
        market_score = _scale_lower(adp, 1.0, 120.0)
        production_score = self._production_score(position, metadata)
        athletic_score = self._athletic_score(position, metadata)
        age_score = _scale_lower(metadata.get("age_at_draft") or player.get("age"), 20.5, 24.5)

        score = (
            model_score * 0.26
            + draft_score * 0.24
            + production_score * 0.24
            + market_score * 0.12
            + athletic_score * 0.08
            + age_score * 0.06
        )
        score = max(score, self._draft_capital_floor(metadata))

        if league_settings.get("superflex") and position == "QB":
            score *= 1.12
        if league_settings.get("ppr") == 1.0 and position in {"WR", "TE"}:
            score *= 1.04
        elif league_settings.get("ppr") == 0.5 and position in {"WR", "TE"}:
            score *= 1.02
        elif league_settings.get("ppr") == 0.0 and position == "RB":
            score *= 1.04
        if league_settings.get("tep") and position == "TE":
            score *= 1.08
        if metadata.get("low_confidence"):
            score *= 0.94
        return _clamp(score)

    def _draft_capital_floor(self, metadata: dict) -> float:
        draft_ovr = _as_float(metadata.get("draft_ovr") or metadata.get("draft_pick"))
        if draft_ovr is None:
            return 0.0
        risk_band = str(metadata.get("risk_band") or "")
        predicted_tier = int(metadata.get("predicted_tier") or 5)
        predicted_bucket = str(metadata.get("predicted_bucket") or "").lower()

        if draft_ovr <= 32 and risk_band != RISK_BAND_HIGH:
            return 78.0 if predicted_bucket == "hit" else 74.0
        if draft_ovr <= 64 and predicted_tier <= 2 and risk_band == RISK_BAND_LOW:
            return 72.0
        return 0.0

    def _production_score(self, position: str, metadata: dict) -> float:
        if position == "WR":
            return (
                _scale_higher(metadata.get("college_yprr"), 1.2, 3.5) * 0.34
                + _scale_higher(metadata.get("college_ypt"), 6.5, 12.5) * 0.20
                + _scale_higher(metadata.get("college_mkt_share_proxy"), 0.70, 0.90) * 0.26
                + _scale_higher(metadata.get("college_td_rate"), 0.04, 0.18) * 0.20
            )
        if position == "RB":
            return (
                _scale_higher(metadata.get("college_ypc"), 4.2, 7.0) * 0.28
                + _scale_higher(metadata.get("college_rush_ypg"), 45.0, 115.0) * 0.28
                + _scale_higher(metadata.get("college_rec_ypg"), 5.0, 32.0) * 0.20
                + _scale_higher(metadata.get("college_mkt_share_proxy"), 0.70, 0.90) * 0.14
                + _scale_higher(metadata.get("college_td_rate"), 0.04, 0.16) * 0.10
            )
        if position == "QB":
            return (
                _scale_higher(metadata.get("college_ypa"), 6.2, 9.4) * 0.30
                + _scale_higher(metadata.get("college_pass_td_rate"), 0.035, 0.10) * 0.24
                + _scale_higher(metadata.get("college_completion_pct_proxy"), 0.58, 0.72) * 0.20
                + _scale_higher(metadata.get("college_qb_rush_ypg"), -5.0, 45.0) * 0.18
                + _scale_higher(metadata.get("college_scramble_rate"), 0.02, 0.14) * 0.08
            )
        if position == "TE":
            return (
                _scale_higher(metadata.get("college_yprr"), 1.0, 2.6) * 0.34
                + _scale_higher(metadata.get("college_ypt"), 6.0, 10.5) * 0.20
                + _scale_higher(metadata.get("college_rec_ypg"), 20.0, 70.0) * 0.20
                + _scale_higher(metadata.get("college_mkt_share_proxy"), 0.65, 0.88) * 0.16
                + _scale_higher(metadata.get("college_td_rate"), 0.03, 0.15) * 0.10
            )
        return 50.0

    def _athletic_score(self, position: str, metadata: dict) -> float:
        forty = metadata.get("forty")
        weight = metadata.get("weight")
        height = metadata.get("height")
        speed_score = _scale_lower(forty, 4.30, 4.75)
        if position == "QB":
            return speed_score * 0.35 + _scale_higher(weight, 205.0, 235.0) * 0.35 + _scale_higher(height, 72.0, 77.0) * 0.30
        if position == "RB":
            return speed_score * 0.50 + _scale_higher(weight, 195.0, 225.0) * 0.35 + _scale_higher(height, 68.0, 73.0) * 0.15
        if position == "WR":
            return speed_score * 0.50 + _scale_higher(weight, 175.0, 215.0) * 0.25 + _scale_higher(height, 69.0, 76.0) * 0.25
        if position == "TE":
            return speed_score * 0.40 + _scale_higher(weight, 230.0, 255.0) * 0.35 + _scale_higher(height, 74.0, 78.0) * 0.25
        return 50.0

    def _assign_tiers(self, players: list[RookiePlayer]) -> list[RookieTier]:
        if not players:
            return []

        tier_buckets: dict[int, list[RookiePlayer]] = {tier: [] for tier in range(1, MAX_TIER_COUNT + 1)}
        for player in players:
            tier_number = self._tier_from_score(player.composite_score)
            tier_buckets[tier_number].append(player.model_copy(update={"tier_number": tier_number}))

        return [
            RookieTier(
                tier_number=tier_number,
                label=TIER_LABELS.get(tier_number, f"Tier {tier_number}"),
                players=tier_players,
            )
            for tier_number, tier_players in tier_buckets.items()
            if tier_players
        ]

    def _tier_from_score(self, score: float) -> int:
        if score >= 85.0:
            return 1
        if score >= 72.0:
            return 2
        if score >= 60.0:
            return 3
        if score >= 48.0:
            return 4
        return 5

    def _assign_archetype(self, player: dict) -> str:
        position = str(player.get("position", ""))
        labels = ARCHETYPE_LABELS.get(position)
        metadata = player.get("metadata", {})
        if metadata.get("archetype_label"):
            return str(metadata["archetype_label"])
        if not labels:
            return ARCHETYPE_FALLBACK_TEMPLATE.format(position=position)
        if not metadata and not player.get("avg_fantasy_points"):
            return ARCHETYPE_FALLBACK_TEMPLATE.format(position=position)

        if position == "WR":
            if float(metadata.get("slot_rate", 0.0) or 0.0) >= 0.55:
                return "Slot Receiver"
            if float(metadata.get("forty", 5.0) or 5.0) <= 4.45:
                return "Deep Threat"
            if int(metadata.get("weight", 0) or 0) >= 210:
                return "Contested Catch WR"
            if float(metadata.get("target_share", 0.0) or 0.0) >= 0.25:
                return "Route Runner"
            return "Possession WR"
        if position == "RB":
            if bool(metadata.get("receiving_back")):
                return "Receiving Back"
            if int(metadata.get("weight", 0) or 0) >= 220:
                return "Power Back"
            if float(player.get("avg_fantasy_points", 0.0) or 0.0) >= 10.0:
                return "Workhorse"
            return "Early Down Back"
        if position == "QB":
            if bool(metadata.get("mobile")) or float(metadata.get("rush_yards", 0.0) or 0.0) >= 400:
                return "Dual Threat QB"
            if float(metadata.get("scramble_rate", 0.0) or 0.0) >= 0.1:
                return "Scrambler"
            if bool(metadata.get("pro_style")):
                return "Pro Style QB"
            return "Pocket Passer"
        if position == "TE":
            if bool(metadata.get("move_te")) or float(metadata.get("slot_rate", 0.0) or 0.0) >= 0.35:
                return "Move TE"
            if bool(metadata.get("h_back")):
                return "H-Back"
            if float(player.get("avg_fantasy_points", 0.0) or 0.0) >= 8.0:
                return "Receiving TE"
            return "Inline Blocker"
        return ARCHETYPE_FALLBACK_TEMPLATE.format(position=position)

    def _assign_risk_band(self, player: dict) -> str:
        metadata = player.get("metadata", {})
        if metadata.get("risk_band") in {RISK_BAND_LOW, RISK_BAND_MODERATE, RISK_BAND_HIGH}:
            return str(metadata["risk_band"])
        position = str(player.get("position", ""))
        age = player.get("age")
        draft_pick = metadata.get("draft_pick")
        injury_flag = bool(metadata.get("injury_flag"))
        production_score = float(metadata.get("production_score", player.get("avg_fantasy_points", 0.0)) or 0.0)
        adp = float(player.get("adp", 999.0))

        if injury_flag:
            return RISK_BAND_HIGH
        if age is not None and int(age) > 23 and position != "QB":
            return RISK_BAND_HIGH
        if draft_pick is not None:
            try:
                if int(draft_pick) > 120:
                    return RISK_BAND_HIGH
                if int(draft_pick) <= 15:
                    return RISK_BAND_LOW
            except (TypeError, ValueError):
                pass
        if adp <= 12 or production_score >= 18:
            return RISK_BAND_LOW
        if adp >= 36:
            return RISK_BAND_HIGH
        return RISK_BAND_MODERATE

    def _compute_class_strength(self, players: list[RookiePlayer]) -> float:
        if not players:
            return 0.0
        tier1_count = sum(1 for player in players if player.tier_number == 1)
        tier2_count = sum(1 for player in players if player.tier_number == 2)
        tier1_delta = (tier1_count - BASELINE_TIER1_COUNT) / max(BASELINE_TIER1_COUNT, 1)
        tier2_delta = (tier2_count - BASELINE_TIER2_COUNT) / max(BASELINE_TIER2_COUNT, 1)
        signal = CLASS_TIER1_WEIGHT * tier1_delta + CLASS_TIER2_WEIGHT * tier2_delta
        return round(max(-1.0, min(1.0, signal)), 4)

    def _build_tendencies(self, scored_rows: list[dict[str, object]]) -> list[dict[str, object]]:
        if not scored_rows:
            return []

        tendencies: list[dict[str, object]] = []
        position_buckets: dict[str, list[float]] = {}
        for row in scored_rows:
            raw = row["raw"]  # type: ignore[assignment]
            player = row["player"]  # type: ignore[assignment]
            adp_rank = int(row["adp_rank"])
            system_rank = int(row["system_rank"])
            delta = system_rank - adp_rank
            position = str(raw["position"])
            position_buckets.setdefault(position, []).append(float(delta))

            if delta >= VALUE_GAP_THRESHOLD:
                tendencies.append(
                    {
                        "tendency_type": "value_gap",
                        "position": position,
                        "player_id": player.player_id,
                        "player_name": player.full_name,
                        "early_draft_slots": None,
                        "adp_delta": round(float(delta), 2),
                        "system_value_slot": system_rank,
                    }
                )

        for position, deltas in position_buckets.items():
            if len(deltas) < TENDENCY_MIN_SAMPLE_SIZE:
                continue
            avg_delta = sum(deltas) / len(deltas)
            if avg_delta >= POSITIONAL_RUN_THRESHOLD:
                tendencies.append(
                    {
                        "tendency_type": "positional_run",
                        "position": position,
                        "player_id": None,
                        "player_name": None,
                        "early_draft_slots": round(avg_delta, 2),
                        "adp_delta": None,
                        "system_value_slot": None,
                    }
                )
        return tendencies

    def _estimate_available_at_slot(
        self,
        board: RookieBoardResult,
        pick_slot: int,
        league_size: int = 12,
    ) -> list[RookiePlayer]:
        formatted_slot = self._format_slot(pick_slot, league_size=league_size)
        players = [
            player
            for tier in board.tiers
            for player in tier.players
            if player.available_probability_by_slot.get(formatted_slot, 0.0) >= 0.5
        ]
        return players

    def _compute_trade_verdict(
        self,
        pick_slot: int,
        board: RookieBoardResult,
        best_player: RookiePlayer | None,
    ) -> TradeVerdict:
        if best_player is None:
            return TradeVerdict(
                verdict="trade",
                label="Trade it",
                reasoning="No significant prospects are likely to reach this slot - trade the pick.",
            )

        if best_player.tier_number == 1:
            return TradeVerdict(
                verdict="use",
                label="Use it",
                reasoning=self._use_reasoning(best_player, board.class_strength_signal),
            )

        if best_player.tier_number == 2 and best_player.composite_score >= STRONG_TIER2_THRESHOLD:
            return TradeVerdict(
                verdict="use",
                label="Use it",
                reasoning=self._use_reasoning(best_player, board.class_strength_signal),
            )

        if (
            board.class_strength_signal < CLASS_WEAKNESS_THRESHOLD
            and pick_slot <= EARLY_PICK_VALUE_THRESHOLD
        ):
            return TradeVerdict(
                verdict="trade",
                label="Trade it",
                reasoning="This class grades weak at the top - move the early pick before the market cools.",
            )

        return TradeVerdict(
            verdict="trade",
            label="Trade it",
            reasoning=f"Your {_format_pick_slot(pick_slot)} carries more market leverage than the likely prospect tier here.",
        )

    def _build_tendency_warnings(
        self,
        tendencies: list[dict],
        available: list[RookiePlayer],
        pick_slot: int,
        league_size: int = 12,
    ) -> list[TendencyWarning]:
        del available, pick_slot
        warnings: list[TendencyWarning] = []
        for tendency in tendencies:
            if tendency.get("tendency_type") == "positional_run":
                early_draft_slots = float(tendency.get("early_draft_slots") or 0.0)
                if early_draft_slots >= POSITIONAL_RUN_THRESHOLD:
                    position = tendency.get("position") or "Players"
                    warnings.append(
                        TendencyWarning(
                            warning_type="positional_run",
                            title=f"{position}s go early in this format",
                            description=f"{position}s come off the board {early_draft_slots:.1f} spots earlier than the board suggests.",
                        )
                    )
            elif tendency.get("tendency_type") == "value_gap":
                adp_delta = float(tendency.get("adp_delta") or 0.0)
                if adp_delta >= VALUE_GAP_THRESHOLD:
                    player_name = tendency.get("player_name") or "A prospect"
                    system_slot = int(tendency.get("system_value_slot") or 1)
                    warnings.append(
                        TendencyWarning(
                            warning_type="value_gap",
                            title=f"{player_name} gets pushed up boards",
                            description=f"Board value says {self._format_slot(system_slot, league_size=league_size)} - market behavior is {adp_delta:.1f} slots earlier.",
                        )
                    )
        return warnings

    def _use_reasoning(self, player: RookiePlayer, class_strength: float) -> str:
        if class_strength > 0.2:
            return f"{player.full_name} sits in a strong tier for this class - use the pick."
        return f"{player.full_name} is still live in your value band - use the pick instead of forcing a trade."

    def _format_label(self, league_settings: dict) -> str:
        parts: list[str] = []
        if league_settings.get("superflex"):
            parts.append("Superflex")
        if league_settings.get("tep"):
            parts.append("TEP")
        ppr = float(league_settings.get("ppr", 0.0) or 0.0)
        if ppr == 1.0:
            parts.append("PPR")
        elif ppr == 0.5:
            parts.append("Half PPR")
        else:
            parts.append("Standard")
        return " · ".join(parts)

    def _format_slot(self, slot: int, league_size: int = 12) -> str:
        return _format_pick_slot(slot, league_size=league_size)


def _format_pick_slot(slot: int, league_size: int = 12) -> str:
    round_number = ((slot - 1) // league_size) + 1
    pick_in_round = ((slot - 1) % league_size) + 1
    return f"{round_number}.{pick_in_round:02d}"

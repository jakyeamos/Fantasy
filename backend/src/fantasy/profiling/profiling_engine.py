from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from statistics import mean
from typing import Any

import duckdb

from fantasy.profiling.constants import (
    ADP_FALLBACK_BY_POSITION,
    EXPLOITATION_TYPE_LABELS,
    EXPLOITATION_TYPE_WEIGHTS,
    MIN_TRADE_EVIDENCE_THRESHOLD,
    PICK_VALUE_NORMALIZED,
    PITCH_ANGLE_VARIANTS,
    SECONDARY_TYPE_THRESHOLD_RATIO,
)
from fantasy.intelligence.constants import (
    CONTENDER_DIRECTION_LABELS,
    REBUILD_DIRECTION_LABELS,
)
from fantasy.profiling.models import (
    ExploitationClassification,
    ManagerProfile,
    PitchAngle,
)


def _loads(raw: str | None, fallback: Any) -> Any:
    if raw is None:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _is_rebuild_direction(direction: str | None) -> bool:
    return direction in REBUILD_DIRECTION_LABELS


def _is_contender_direction(direction: str | None) -> bool:
    return direction in CONTENDER_DIRECTION_LABELS


def _format_label(label: str | None, fallback: str) -> str:
    if label is None:
        return fallback
    return label.replace("_", " ")


class ProfilingEngine:
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self._conn = conn

    def _load_trades(self, league_id: str, roster_id: int) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT transaction_id, created_at, roster_ids, adds, drops, draft_picks, week
            FROM transactions
            WHERE league_id = ? AND type = 'trade'
            ORDER BY created_at ASC NULLS LAST, transaction_id ASC
            """,
            [league_id],
        ).fetchall()
        trades: list[dict[str, Any]] = []
        for row in rows:
            roster_ids = [int(value) for value in _loads(row[2], [])]
            if roster_id not in roster_ids:
                continue
            trades.append(
                {
                    "transaction_id": str(row[0]),
                    "created_at": row[1],
                    "roster_ids": roster_ids,
                    "adds": _loads(row[3], {}),
                    "drops": _loads(row[4], {}),
                    "draft_picks": _loads(row[5], []),
                    "week": int(row[6] or 0),
                }
            )
        return trades

    def _parse_trade_sides(
        self, transaction: dict[str, Any], roster_id: int
    ) -> tuple[list[str], list[str], list[int], list[int]]:
        adds = transaction.get("adds", {})
        drops = transaction.get("drops", {})
        picks = transaction.get("draft_picks", [])
        received = [
            str(player_id)
            for player_id, target_roster in adds.items()
            if int(target_roster) == roster_id
        ]
        sent = [
            str(player_id)
            for player_id, source_roster in drops.items()
            if int(source_roster) == roster_id
        ]
        received_pick_rounds = [
            int(pick.get("round"))
            for pick in picks
            if pick.get("owner_id") is not None and int(pick.get("owner_id")) == roster_id
        ]
        sent_pick_rounds = [
            int(pick.get("round"))
            for pick in picks
            if pick.get("previous_owner_id") is not None
            and int(pick.get("previous_owner_id")) == roster_id
        ]
        return received, sent, received_pick_rounds, sent_pick_rounds

    def _load_adp_values(self, player_ids: list[str]) -> dict[str, float]:
        if not player_ids:
            return {}
        placeholders = ",".join("?" for _ in player_ids)
        max_row = self._conn.execute(
            "SELECT COALESCE(MAX(adp), 200.0) FROM player_adp_baseline"
        ).fetchone()
        max_adp = float(max_row[0]) if max_row and max_row[0] is not None else 200.0
        rows = self._conn.execute(
            f"""
            SELECT p.player_id, p.position, b.adp
            FROM players p
            LEFT JOIN player_adp_baseline b ON b.player_id = p.player_id
            WHERE p.player_id IN ({placeholders})
            """,
            player_ids,
        ).fetchall()
        adp_map: dict[str, float] = {}
        for row in rows:
            player_id = str(row[0])
            position = str(row[1] or "UNKNOWN")
            adp = row[2]
            if adp is None:
                adp_map[player_id] = ADP_FALLBACK_BY_POSITION.get(
                    position, ADP_FALLBACK_BY_POSITION["UNKNOWN"]
                )
                continue
            adp_map[player_id] = max(0.0, 1.0 - (float(adp) / max_adp))
        for player_id in player_ids:
            adp_map.setdefault(player_id, ADP_FALLBACK_BY_POSITION["UNKNOWN"])
        return adp_map

    def _compute_value_delta(
        self,
        received_ids: list[str],
        sent_ids: list[str],
        received_pick_rounds: list[int] | None = None,
        sent_pick_rounds: list[int] | None = None,
        adp_map: dict[str, float] | None = None,
    ) -> float:
        adp_map = adp_map or {}
        received_value = sum(adp_map.get(player_id, 0.0) for player_id in received_ids)
        sent_value = sum(adp_map.get(player_id, 0.0) for player_id in sent_ids)
        received_value += sum(
            PICK_VALUE_NORMALIZED.get(round_number, 0.05)
            for round_number in (received_pick_rounds or [])
        )
        sent_value += sum(
            PICK_VALUE_NORMALIZED.get(round_number, 0.05)
            for round_number in (sent_pick_rounds or [])
        )
        return received_value - sent_value

    def _load_direction(self, league_id: str, roster_id: int) -> str | None:
        row = self._conn.execute(
            """
            SELECT primary_label
            FROM team_directions
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        return str(row[0]) if row is not None else None

    def _load_player_ages(self, player_ids: list[str]) -> dict[str, int]:
        if not player_ids:
            return {}
        placeholders = ",".join("?" for _ in player_ids)
        rows = self._conn.execute(
            f"SELECT player_id, age FROM players WHERE player_id IN ({placeholders})",
            player_ids,
        ).fetchall()
        return {
            str(row[0]): int(row[1]) for row in rows if row[1] is not None
        }

    def _load_player_positions(self, player_ids: list[str]) -> dict[str, str]:
        if not player_ids:
            return {}
        placeholders = ",".join("?" for _ in player_ids)
        rows = self._conn.execute(
            f"SELECT player_id, position FROM players WHERE player_id IN ({placeholders})",
            player_ids,
        ).fetchall()
        return {str(row[0]): str(row[1] or "UNKNOWN") for row in rows}

    def _load_player_names(self, player_ids: list[str]) -> dict[str, str]:
        if not player_ids:
            return {}
        placeholders = ",".join("?" for _ in player_ids)
        rows = self._conn.execute(
            f"SELECT player_id, full_name FROM players WHERE player_id IN ({placeholders})",
            player_ids,
        ).fetchall()
        return {str(row[0]): str(row[1] or row[0]) for row in rows}

    def _timing_error_count(
        self, trades: list[dict[str, Any]], roster_id: int
    ) -> int:
        evidence = 0
        for trade in trades:
            received, sent, _, _ = self._parse_trade_sides(trade, roster_id)
            week = int(trade.get("week") or 0)
            if week <= 1:
                continue
            triggered = False
            for player_id, mode in [(pid, "received") for pid in received] + [
                (pid, "sent") for pid in sent
            ]:
                rows = self._conn.execute(
                    """
                    SELECT fantasy_points
                    FROM player_stats_weekly
                    WHERE player_id = ? AND week BETWEEN ? AND ?
                    ORDER BY week
                    """,
                    [player_id, max(1, week - 3), max(1, week - 1)],
                ).fetchall()
                history = [float(row[0]) for row in rows if row[0] is not None]
                if not history:
                    continue
                season_row = self._conn.execute(
                    """
                    SELECT AVG(fantasy_points)
                    FROM player_stats_weekly
                    WHERE player_id = ?
                    """,
                    [player_id],
                ).fetchone()
                season_avg = float(season_row[0]) if season_row and season_row[0] is not None else 0.0
                if season_avg <= 0:
                    continue
                recent_avg = mean(history)
                if mode == "received" and recent_avg >= season_avg * 1.2:
                    triggered = True
                if mode == "sent" and recent_avg <= season_avg * 0.8:
                    triggered = True
            evidence += int(triggered)
        return evidence

    def _classify_exploitation(
        self,
        trades: list[dict[str, Any]],
        roster_id: int,
        direction: str | None,
        adp_map: dict[str, float],
    ) -> ExploitationClassification:
        total_trades = len(trades)
        if total_trades == 0:
            return ExploitationClassification(
                primary_type=None,
                secondary_type=None,
                evidence_strings={},
                evidence_counts={},
                metadata={},
            )

        player_pool = sorted(
            {
                player_id
                for trade in trades
                for player_id in (
                    self._parse_trade_sides(trade, roster_id)[0]
                    + self._parse_trade_sides(trade, roster_id)[1]
                )
            }
        )
        ages = self._load_player_ages(player_pool)
        positions = self._load_player_positions(player_pool)

        deltas: list[float] = []
        negative_count = 0
        directional_incoherence = 0
        overpay_by_position: dict[str, list[float]] = defaultdict(list)
        sent_pick_trades = 0
        for trade in trades:
            received, sent, received_picks, sent_picks = self._parse_trade_sides(trade, roster_id)
            delta = self._compute_value_delta(
                received,
                sent,
                received_pick_rounds=received_picks,
                sent_pick_rounds=sent_picks,
                adp_map=adp_map,
            )
            deltas.append(delta)
            if delta < 0:
                negative_count += 1
            received_positions = [positions.get(player_id, "UNKNOWN") for player_id in received]
            for position in received_positions:
                overpay_by_position[position].append(delta)
            if sent_picks:
                sent_pick_trades += 1
            if direction is not None:
                received_ages = [ages.get(player_id, 0) for player_id in received]
                if _is_rebuild_direction(direction):
                    if sent_picks or any(age >= 27 for age in received_ages):
                        directional_incoherence += 1
                if _is_contender_direction(direction):
                    sent_ages = [ages.get(player_id, 0) for player_id in sent]
                    if any(age <= 23 for age in sent_ages) and not received:
                        directional_incoherence += 1

        win_rate = (
            sum(1 for delta in deltas if delta > 0) / total_trades if total_trades else 0.0
        )
        avg_delta = mean(deltas) if deltas else 0.0
        timing_error = self._timing_error_count(trades, roster_id)

        overpay_position = None
        overpay_count = 0
        for position, position_deltas in overpay_by_position.items():
            negatives = [delta for delta in position_deltas if delta < -0.10]
            if len(negatives) >= 3 and len(negatives) > overpay_count:
                overpay_position = position
                overpay_count = len(negatives)

        evidence_counts = {
            "value_loss": negative_count if win_rate < 0.40 or avg_delta < 0 else 0,
            "timing_error": timing_error,
            "directional_incoherence": directional_incoherence if direction is not None else 0,
            "archetype_overpay": overpay_count,
        }
        sorted_types = sorted(
            evidence_counts.items(),
            key=lambda item: (item[1], EXPLOITATION_TYPE_WEIGHTS.get(item[0], 0.0)),
            reverse=True,
        )
        primary_type = sorted_types[0][0] if sorted_types and sorted_types[0][1] > 0 else None
        secondary_type = None
        if primary_type is not None and len(sorted_types) > 1:
            secondary_candidate, secondary_count = sorted_types[1]
            primary_count = evidence_counts[primary_type]
            if secondary_count > 0 and secondary_count >= math.ceil(
                primary_count * SECONDARY_TYPE_THRESHOLD_RATIO
            ):
                secondary_type = secondary_candidate

        evidence_strings = {
            "value_loss": f"Lost value on {negative_count} of {total_trades} trades",
            "timing_error": f"Sold during value trough on {timing_error} of {total_trades} trades",
            "directional_incoherence": (
                f"{directional_incoherence} trades contradict {direction} direction"
                if direction is not None
                else "Direction data unavailable"
            ),
            "archetype_overpay": (
                f"Overpaid for {overpay_position} in {overpay_count} of {len(overpay_by_position.get(overpay_position, []))} trades"
                if overpay_position is not None
                else "Overpaid for UNKNOWN in 0 of 0 trades"
            ),
        }
        return ExploitationClassification(
            primary_type=primary_type,
            secondary_type=secondary_type,
            evidence_strings=evidence_strings,
            evidence_counts=evidence_counts,
            metadata={
                "avg_delta": avg_delta,
                "win_rate": win_rate,
                "focus_position": overpay_position,
                "sent_pick_trades": sent_pick_trades,
                "trade_count": total_trades,
            },
        )

    def _compute_score(
        self,
        total_trades: int,
        exploitation: ExploitationClassification,
    ) -> float:
        if total_trades <= 0:
            return 0.0
        weighted = 0.0
        for exploitation_type, weight in EXPLOITATION_TYPE_WEIGHTS.items():
            weighted += (
                exploitation.evidence_counts.get(exploitation_type, 0) / total_trades
            ) * weight
        return round(min(weighted * 100.0, 100.0), 2)

    def _pitch_angle_context(
        self,
        exploitation: ExploitationClassification,
        direction: str | None,
    ) -> dict[str, str | int | float]:
        focus_position = str(exploitation.metadata.get("focus_position") or "").upper()
        focus_position_label = (
            focus_position if focus_position and focus_position != "UNKNOWN" else "position-specific"
        )
        if focus_position == "QB":
            focus_asset_phrase = "QB2 or volatile quarterback depth"
        elif focus_position and focus_position != "UNKNOWN":
            focus_asset_phrase = f"{focus_position} depth with insulation attached"
        else:
            focus_asset_phrase = "depth at the spot they keep chasing"

        trade_count = int(exploitation.metadata.get("trade_count", 0))
        negative_count = int(exploitation.evidence_counts.get("value_loss", 0))
        sent_pick_trades = int(exploitation.metadata.get("sent_pick_trades", 0))
        avg_delta = float(exploitation.metadata.get("avg_delta", 0.0))
        return {
            "direction_label": _format_label(direction, "current roster path"),
            "focus_position_label": focus_position_label,
            "focus_asset_phrase": focus_asset_phrase,
            "trade_count": trade_count,
            "negative_count": negative_count,
            "negative_trade_phrase": f"{negative_count} of {trade_count}",
            "sent_pick_trades": sent_pick_trades,
            "avg_delta": round(avg_delta, 3),
        }

    def _candidate_pitch_families(
        self,
        exploitation: ExploitationClassification,
        direction: str | None,
    ) -> list[str]:
        rebuild = _is_rebuild_direction(direction)
        avg_delta = float(exploitation.metadata.get("avg_delta", 0.0))
        sent_pick_trades = int(exploitation.metadata.get("sent_pick_trades", 0))
        focus_position = str(exploitation.metadata.get("focus_position") or "").upper()
        primary = exploitation.primary_type
        secondary = exploitation.secondary_type
        families: list[str] = []

        if primary == "value_loss":
            if rebuild:
                if sent_pick_trades >= 2:
                    families.append("value_loss_rebuild_pick_pressure")
                families.append("value_loss_rebuild_insulation")
                families.append(
                    "directional_incoherence_pick_drift"
                    if secondary == "directional_incoherence"
                    else "timing_error_rebuild_patience"
                )
                families.append("timing_error_rebuild_trough_buyback")
            else:
                families.append(
                    "value_loss_contender_points_patch"
                    if avg_delta <= -0.10
                    else "value_loss_contender_future_leak"
                )
                families.append(
                    "timing_error_contender_box_score"
                    if secondary == "timing_error"
                    else "directional_incoherence_reset"
                )
                families.append("timing_error_contender_spike_sale")
                families.append("value_loss_contender_future_leak")
        elif primary == "timing_error":
            if rebuild:
                families.append(
                    "timing_error_rebuild_patience"
                    if sent_pick_trades >= 1
                    else "timing_error_rebuild_trough_buyback"
                )
                families.append(
                    "value_loss_rebuild_pick_pressure"
                    if sent_pick_trades >= 2
                    else "value_loss_rebuild_insulation"
                )
                families.append("directional_incoherence_pick_drift")
            else:
                families.extend(
                    [
                        "timing_error_contender_spike_sale",
                        "timing_error_contender_box_score",
                        "value_loss_contender_points_patch",
                    ]
                )
        elif primary == "directional_incoherence":
            if rebuild:
                families.extend(
                    [
                        "directional_incoherence_pick_drift",
                        "value_loss_rebuild_pick_pressure"
                        if sent_pick_trades >= 1
                        else "value_loss_rebuild_insulation",
                        "timing_error_rebuild_patience",
                    ]
                )
            else:
                families.extend(
                    [
                        "directional_incoherence_reset",
                        "value_loss_contender_points_patch",
                        "timing_error_contender_box_score",
                    ]
                )
        else:
            if focus_position == "QB":
                families.extend(["archetype_overpay_qb_patch", "archetype_overpay_qb_ceiling"])
            else:
                families.append("archetype_overpay_position")
            families.append(
                "value_loss_rebuild_insulation" if rebuild else "value_loss_contender_points_patch"
            )
            families.append(
                "timing_error_rebuild_patience" if rebuild else "timing_error_contender_spike_sale"
            )

        if secondary == "timing_error":
            families.append(
                "timing_error_rebuild_trough_buyback"
                if rebuild
                else "timing_error_contender_box_score"
            )
        elif secondary == "directional_incoherence":
            families.append(
                "directional_incoherence_pick_drift"
                if rebuild
                else "directional_incoherence_reset"
            )
        elif secondary == "value_loss":
            families.append(
                "value_loss_rebuild_insulation"
                if rebuild
                else "value_loss_contender_future_leak"
            )
        elif secondary == "archetype_overpay":
            families.append(
                "archetype_overpay_qb_patch"
                if focus_position == "QB"
                else "archetype_overpay_position"
            )

        ordered: list[str] = []
        for family in families:
            if family not in ordered:
                ordered.append(family)
        return ordered

    def _render_pitch_angle(
        self,
        family: str,
        rank: int,
        context: dict[str, str | int | float],
    ) -> PitchAngle | None:
        variants = PITCH_ANGLE_VARIANTS.get(family)
        if not variants:
            return None
        seed = (
            int(abs(float(context["avg_delta"])) * 1000)
            + int(context["trade_count"]) * 3
            + int(context["negative_count"]) * 5
            + int(context["sent_pick_trades"]) * 7
            + len(family)
            + rank
        )
        template = variants[seed % len(variants)]
        return PitchAngle(
            rank=rank,
            deal_archetype=template["deal_archetype"].format(**context),
            send_description=template["send_template"].format(**context),
            avoid_description=template["avoid_template"].format(**context),
            reasoning=template["reasoning_template"].format(**context),
        )

    def _compute_pitch_angles(
        self,
        exploitation: ExploitationClassification,
        direction: str | None,
    ) -> list[PitchAngle]:
        if exploitation.primary_type is None:
            return []

        keys = self._candidate_pitch_families(exploitation, direction)
        context = self._pitch_angle_context(exploitation, direction)
        angles: list[PitchAngle] = []
        for rank, key in enumerate(keys, start=1):
            angle = self._render_pitch_angle(key, rank, context)
            if angle is None:
                continue
            angles.append(angle)
        return angles[:3]

    def _pick_descriptions(
        self, transaction: dict[str, Any], roster_id: int
    ) -> tuple[list[str], list[str]]:
        sent: list[str] = []
        received: list[str] = []
        for pick in transaction.get("draft_picks", []):
            season = str(pick.get("season") or "Unknown")
            round_number = int(pick.get("round") or 0)
            label = f"{season} Round {round_number} pick"
            if pick.get("owner_id") is not None and int(pick.get("owner_id")) == roster_id:
                received.append(label)
            if (
                pick.get("previous_owner_id") is not None
                and int(pick.get("previous_owner_id")) == roster_id
            ):
                sent.append(label)
        return sent, received

    def _build_trade_history(
        self,
        trades: list[dict[str, Any]],
        roster_id: int,
        adp_map: dict[str, float],
    ) -> list[dict[str, Any]]:
        player_ids = sorted(
            {
                player_id
                for trade in trades
                for player_id in (
                    self._parse_trade_sides(trade, roster_id)[0]
                    + self._parse_trade_sides(trade, roster_id)[1]
                )
            }
        )
        names = self._load_player_names(player_ids)
        history: list[dict[str, Any]] = []
        for trade in trades:
            received, sent, received_picks, sent_picks = self._parse_trade_sides(trade, roster_id)
            value_delta = self._compute_value_delta(
                received,
                sent,
                received_pick_rounds=received_picks,
                sent_pick_rounds=sent_picks,
                adp_map=adp_map,
            )
            sent_pick_assets, received_pick_assets = self._pick_descriptions(
                trade, roster_id
            )
            sent_assets = [names.get(player_id, player_id) for player_id in sent] + sent_pick_assets
            received_assets = [names.get(player_id, player_id) for player_id in received] + received_pick_assets
            created_at = trade.get("created_at")
            history.append(
                {
                    "transaction_id": trade.get("transaction_id"),
                    "date": created_at.isoformat() if created_at is not None else None,
                    "sent_assets": sent_assets,
                    "received_assets": received_assets,
                    "value_delta": round(value_delta, 3),
                }
            )
        history.sort(key=lambda item: item["date"] or "", reverse=True)
        return history

    def _compute_behavioral_fields(
        self,
        trades: list[dict[str, Any]],
        roster_id: int,
        direction: str | None,
        exploitation: ExploitationClassification,
        deltas: list[float],
    ) -> dict[str, Any]:
        total = len(trades)
        low_confidence = total < MIN_TRADE_EVIDENCE_THRESHOLD

        avg_delta = float(exploitation.metadata.get("avg_delta", 0.0))
        win_rate = float(exploitation.metadata.get("win_rate", 0.0))
        sent_pick_trades = int(exploitation.metadata.get("sent_pick_trades", 0))
        rebuild = _is_rebuild_direction(direction)
        contender = _is_contender_direction(direction)

        if total == 0:
            urgency_state = "stable"
        elif rebuild and sent_pick_trades >= 2:
            urgency_state = "building_urgency"
        elif contender and avg_delta < -0.10 and win_rate < 0.35:
            urgency_state = "panic_mode"
        elif contender and win_rate < 0.40:
            urgency_state = "declining_window"
        else:
            urgency_state = "stable"

        early_trades = sum(
            1
            for trade in trades
            if 1 <= int(trade.get("week") or 0) <= 5
        )
        toc_sensitivity = (
            round(min(early_trades / max(total, 1), 1.0), 3) if total > 0 else 0.0
        )

        received_ages: list[int] = []
        for trade in trades:
            received, _, _, _ = self._parse_trade_sides(trade, roster_id)
            ages = self._load_player_ages(received)
            received_ages.extend(ages.values())
        vet_count = sum(1 for age in received_ages if age >= 27)
        veteran_appetite = (
            round(min(vet_count / max(len(received_ages), 1), 1.0), 3)
            if received_ages
            else 0.0
        )

        arch_count = int(exploitation.evidence_counts.get("archetype_overpay", 0))
        focus_pos = str(exploitation.metadata.get("focus_position") or "").upper()
        if arch_count >= 3 and focus_pos in ("WR", "RB"):
            rookie_fever_index = round(min(arch_count / max(total, 1), 1.0), 3)
        else:
            rookie_fever_index = 0.0

        neg_count = int(exploitation.evidence_counts.get("value_loss", 0))
        timing_count = int(exploitation.evidence_counts.get("timing_error", 0))
        if total >= 3:
            rigidity_raw = (neg_count + timing_count) / (2 * total)
            value_rigidity = round(min(rigidity_raw, 1.0), 3)
        else:
            value_rigidity = 0.0

        reroute_susceptibility = (
            round(min(sent_pick_trades / max(total, 1), 1.0), 3) if total > 0 else 0.0
        )

        if total == 0:
            motivations = "Insufficient trade evidence to determine motivations."
        elif urgency_state == "panic_mode":
            motivations = (
                f"Likely panic selling - win-rate of {round(win_rate * 100)}% and average "
                "value loss suggest desperation moves. Capitalize before they stabilize."
            )
        elif urgency_state == "building_urgency":
            dir_label = _format_label(direction, "current path")
            motivations = (
                f"Actively building - trading picks into a {dir_label} roster. Most "
                "receptive to player-for-pick offers that accelerate their timeline."
            )
        elif urgency_state == "declining_window":
            motivations = (
                f"Window is shrinking - win-rate of {round(win_rate * 100)}% suggests "
                "mounting pressure to improve now. Likely to overpay for proven production."
            )
        elif veteran_appetite >= 0.5:
            motivations = (
                "Strong preference for proven veterans - this manager repeatedly acquires "
                "aging talent. Target their young assets and picks."
            )
        elif rookie_fever_index >= 0.3:
            motivations = (
                f"Overvalues current-year {focus_pos} talent - overpaid in {arch_count} trades. "
                "Surface veterans or off-trend positions to exploit this gap."
            )
        else:
            motivations = (
                "No dominant behavioral pattern detected. Use pitch angle guidance for "
                "approach recommendations."
            )

        if low_confidence:
            best_target = None
        elif urgency_state == "panic_mode":
            best_target = "Their best young player or early first - panic sellers offer more than the market requires."
        elif urgency_state == "building_urgency" and sent_pick_trades >= 3:
            best_target = "Future first-round picks - they have been selling picks and may price them below market."
        elif rookie_fever_index >= 0.3 and focus_pos in ("WR", "RB"):
            best_target = f"Established veterans at {focus_pos} - they overvalue current-year youth and may sell proven talent too cheaply."
        elif veteran_appetite >= 0.5:
            best_target = "Their young pass-catchers or developmental players - youth is likely undervalued on this roster."
        else:
            best_target = None

        if low_confidence:
            best_send = None
        elif urgency_state in ("panic_mode", "declining_window"):
            best_send = "A proven starter - even aging production can satisfy their urgency, especially with a small sweetener."
        elif rookie_fever_index >= 0.3 and focus_pos in ("WR", "RB"):
            best_send = f"Current-year {focus_pos} prospects or recent draft picks at that position - they overpay reliably for this appetite."
        elif veteran_appetite >= 0.5:
            best_send = "A veteran contributor at a position of need - they consistently pay above market for aging talent."
        elif reroute_susceptibility >= 0.4:
            best_send = "A pick-inclusive offer - they engage readily with pick-based structures and may accept a tiered package."
        else:
            best_send = None

        return {
            "likely_motivations_now": motivations,
            "recent_urgency_state": urgency_state,
            "time_of_calendar_sensitivity": toc_sensitivity,
            "veteran_appetite": veteran_appetite,
            "rookie_fever_index": rookie_fever_index,
            "value_rigidity": value_rigidity,
            "reroute_susceptibility": reroute_susceptibility,
            "best_asset_to_target": best_target,
            "best_asset_to_send": best_send,
        }

    def compute_profile(self, league_id: str, roster_id: int) -> ManagerProfile:
        trades = self._load_trades(league_id, roster_id)
        all_players = sorted(
            {
                player_id
                for trade in trades
                for player_id in (
                    self._parse_trade_sides(trade, roster_id)[0]
                    + self._parse_trade_sides(trade, roster_id)[1]
                )
            }
        )
        adp_map = self._load_adp_values(all_players)
        direction = self._load_direction(league_id, roster_id)
        exploitation = self._classify_exploitation(trades, roster_id, direction, adp_map)
        exploitability_score = self._compute_score(len(trades), exploitation)
        pitch_angles = self._compute_pitch_angles(exploitation, direction)

        deltas = []
        for trade in trades:
            received, sent, received_picks, sent_picks = self._parse_trade_sides(trade, roster_id)
            deltas.append(
                self._compute_value_delta(
                    received,
                    sent,
                    received_pick_rounds=received_picks,
                    sent_pick_rounds=sent_picks,
                    adp_map=adp_map,
                )
            )
        avg_delta = round(mean(deltas), 3) if deltas else 0.0
        win_rate = round(
            sum(1 for delta in deltas if delta > 0) / len(deltas), 3
        ) if deltas else 0.0

        roster_row = self._conn.execute(
            """
            SELECT owner_id, owner_display_name, players
            FROM rosters
            WHERE league_id = ? AND roster_id = ?
            LIMIT 1
            """,
            [league_id, roster_id],
        ).fetchone()
        manager_name = (
            str(roster_row[1] or roster_row[0])
            if roster_row and (roster_row[1] or roster_row[0])
            else f"Roster {roster_id}"
        )
        roster_players = _loads(roster_row[2], []) if roster_row else []
        position_counts = Counter(
            str(row[0] or "UNKNOWN")
            for row in self._conn.execute(
                """
                SELECT position
                FROM players
                WHERE player_id IN ({})
                """.format(",".join("?" for _ in roster_players))
                if roster_players
                else "SELECT NULL WHERE FALSE",
                roster_players if roster_players else [],
            ).fetchall()
        )

        weakest_positions = sorted(position_counts.items(), key=lambda item: item[1])[:2]
        low_confidence = len(trades) < MIN_TRADE_EVIDENCE_THRESHOLD
        roster_summary = {
            "manager_name": manager_name,
            "direction_label": direction,
            "positional_needs": [position for position, _ in weakest_positions],
            "roster_size": len(roster_players),
        }
        aggregate_trade_stats = {
            "total_trades": len(trades),
            "win_rate": win_rate,
            "avg_delta": avg_delta,
        }
        behavioral = self._compute_behavioral_fields(
            trades,
            roster_id,
            direction,
            exploitation,
            deltas,
        )
        return ManagerProfile(
            league_id=league_id,
            roster_id=roster_id,
            computed_at=datetime.now(tz=timezone.utc).isoformat(),
            manager_name=manager_name,
            direction_label=direction,
            evidence_count=len(trades),
            low_confidence=low_confidence,
            exploitability_score=exploitability_score,
            exploitation_primary=exploitation.primary_type,
            exploitation_secondary=exploitation.secondary_type,
            exploitation_evidence=exploitation.evidence_strings,
            pitch_angles=pitch_angles,
            trade_history=self._build_trade_history(trades, roster_id, adp_map),
            aggregate_trade_stats=aggregate_trade_stats,
            roster_summary=roster_summary,
            likely_motivations_now=behavioral["likely_motivations_now"],
            recent_urgency_state=behavioral["recent_urgency_state"],
            time_of_calendar_sensitivity=behavioral["time_of_calendar_sensitivity"],
            veteran_appetite=behavioral["veteran_appetite"],
            rookie_fever_index=behavioral["rookie_fever_index"],
            value_rigidity=behavioral["value_rigidity"],
            reroute_susceptibility=behavioral["reroute_susceptibility"],
            best_asset_to_target=behavioral["best_asset_to_target"],
            best_asset_to_send=behavioral["best_asset_to_send"],
        )

    def compute_all_profiles(self, league_id: str) -> list[ManagerProfile]:
        rows = self._conn.execute(
            """
            SELECT roster_id
            FROM rosters
            WHERE league_id = ?
            ORDER BY roster_id
            """,
            [league_id],
        ).fetchall()
        return [self.compute_profile(league_id, int(row[0])) for row in rows]

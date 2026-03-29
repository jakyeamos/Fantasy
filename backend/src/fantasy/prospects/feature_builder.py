from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

import polars as pl

from fantasy.prospects.constants import HISTORICAL_START_YEAR, POSITIONS
from fantasy.prospects.models import ProspectFeatures


def _row_value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_birth_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    text = str(value)
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _safe_divide(numerator: float | None, denominator: float | int | None) -> float | None:
    if numerator is None or denominator in (None, 0, 0.0):
        return None
    try:
        return float(numerator) / float(denominator)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _normalize_name(value: Any) -> str:
    if value in (None, ""):
        return ""
    return "".join(ch.lower() for ch in str(value) if ch.isalnum())


def derive_college_profile(row: dict[str, Any], position: str) -> dict[str, float | int | None]:
    games = _as_int(_row_value(row, "college_games", "games", "gp"))
    targets = _as_float(_row_value(row, "college_targets", "targets"))
    receptions = _as_float(_row_value(row, "college_receptions", "receptions"))
    receiving_yards = _as_float(
        _row_value(row, "college_receiving_yards", "receiving_yards", "rec_yards")
    )
    receiving_tds = _as_float(
        _row_value(row, "college_receiving_tds", "receiving_tds", "rec_tds")
    )
    routes_run = _as_float(_row_value(row, "college_routes_run", "routes_run"))
    carries = _as_float(_row_value(row, "college_carries", "carries", "rushing_attempts", "rush_attempts"))
    rushing_yards = _as_float(
        _row_value(row, "college_rushing_yards", "rushing_yards", "rush_yards")
    )
    rushing_tds = _as_float(_row_value(row, "college_rushing_tds", "rushing_tds", "rush_tds"))
    pass_attempts = _as_float(_row_value(row, "college_pass_attempts", "pass_attempts", "attempts"))
    completions = _as_float(_row_value(row, "college_completions", "completions"))
    passing_yards = _as_float(
        _row_value(row, "college_passing_yards", "passing_yards", "pass_yards")
    )
    passing_tds = _as_float(_row_value(row, "college_passing_tds", "passing_tds", "pass_tds"))
    interceptions = _as_float(_row_value(row, "college_interceptions", "interceptions", "pass_ints"))
    target_share = _as_float(
        _row_value(
            row,
            "college_mkt_share_proxy",
            "target_share",
            "dominator",
            "receiving_yards_share",
            "yard_share",
        )
    )
    completion_pct = _as_float(_row_value(row, "college_completion_pct_proxy", "completion_pct"))
    yprr = _as_float(
        _row_value(row, "college_yprr", "yards_per_route_run", "receiving_yards_per_route_run")
    )
    ypt = _as_float(
        _row_value(row, "college_ypt", "yards_per_target", "receiving_yards_per_target")
    )
    ypc = _as_float(_row_value(row, "college_ypc", "yards_per_carry", "rushing_yards_per_carry"))
    ypa = _as_float(_row_value(row, "college_ypa", "yards_per_attempt", "passing_yards_per_attempt"))
    pass_td_rate = _as_float(_row_value(row, "college_pass_td_rate", "passing_td_rate"))
    qb_rush_yards = _as_float(
        _row_value(row, "college_qb_rush_yards", "qb_rush_yards", "quarterback_rush_yards")
    )
    qb_rush_tds = _as_float(_row_value(row, "college_qb_rush_tds", "qb_rush_tds", "quarterback_rush_tds"))
    qb_rush_ypg = _as_float(_row_value(row, "college_qb_rush_ypg", "qb_rush_ypg"))
    scramble_rate = _as_float(_row_value(row, "college_scramble_rate", "scramble_rate"))
    college_rec_ypg = _as_float(_row_value(row, "college_rec_ypg", "receiving_yards_per_game"))
    college_rush_ypg = _as_float(_row_value(row, "college_rush_ypg", "rushing_yards_per_game"))
    college_td_rate = _as_float(_row_value(row, "college_td_rate", "td_rate"))

    if qb_rush_yards is None and position == "QB":
        qb_rush_yards = rushing_yards
    if qb_rush_tds is None and position == "QB":
        qb_rush_tds = rushing_tds

    if college_rec_ypg is None:
        college_rec_ypg = _safe_divide(receiving_yards, games)
    if college_rush_ypg is None:
        college_rush_ypg = _safe_divide(rushing_yards, games)
    if completion_pct is None:
        completion_pct = _safe_divide(completions, pass_attempts)
    if yprr is None:
        yprr = _safe_divide(receiving_yards, routes_run)
    if ypt is None:
        ypt = _safe_divide(receiving_yards, targets)
    if ypc is None:
        ypc = _safe_divide(rushing_yards, carries)
    if ypa is None:
        ypa = _safe_divide(passing_yards, pass_attempts)
    if pass_td_rate is None:
        pass_td_rate = _safe_divide(passing_tds, pass_attempts)
    if qb_rush_ypg is None:
        qb_rush_ypg = _safe_divide(qb_rush_yards, games)

    if college_td_rate is None:
        if position in {"WR", "TE"}:
            college_td_rate = _safe_divide(receiving_tds, receptions)
        elif position == "RB":
            college_td_rate = _safe_divide(rushing_tds, carries)

    return {
        "college_games": games,
        "college_targets": targets,
        "college_receptions": receptions,
        "college_receiving_yards": receiving_yards,
        "college_receiving_tds": receiving_tds,
        "college_routes_run": routes_run,
        "college_carries": carries,
        "college_rushing_yards": rushing_yards,
        "college_rushing_tds": rushing_tds,
        "college_pass_attempts": pass_attempts,
        "college_completions": completions,
        "college_passing_yards": passing_yards,
        "college_passing_tds": passing_tds,
        "college_interceptions": interceptions,
        "college_rec_ypg": college_rec_ypg,
        "college_rush_ypg": college_rush_ypg,
        "college_yprr": yprr,
        "college_ypt": ypt,
        "college_ypc": ypc,
        "college_ypa": ypa,
        "college_pass_td_rate": pass_td_rate,
        "college_qb_rush_yards": qb_rush_yards,
        "college_qb_rush_tds": qb_rush_tds,
        "college_qb_rush_ypg": qb_rush_ypg,
        "college_scramble_rate": scramble_rate,
        "college_mkt_share_proxy": target_share,
        "college_td_rate": college_td_rate,
        "college_completion_pct_proxy": completion_pct,
    }


class FeatureBuilder:
    def __init__(
        self,
        combine_df: pl.DataFrame,
        players_df: pl.DataFrame,
        draft_df: pl.DataFrame,
        weekly_stats_df: pl.DataFrame,
        adp_lookup: dict[str, float] | None = None,
    ):
        self._combine_rows = combine_df.to_dicts() if combine_df.height else []
        self._player_rows = players_df.to_dicts() if players_df.height else []
        self._draft_rows = draft_df.to_dicts() if draft_df.height else []
        self._weekly_rows = weekly_stats_df.to_dicts() if weekly_stats_df.height else []
        self._adp_lookup = adp_lookup or {}

    def build_all_features(
        self,
        current_class_year: int,
        positions: list[str] | None = None,
    ) -> list[ProspectFeatures]:
        target_positions = set(positions or POSITIONS)
        combine_by_id = self._index_rows(self._combine_rows)
        combine_by_name = self._index_rows(self._combine_rows, by_name=True)
        players_by_id = self._index_rows(self._player_rows)
        players_by_name = self._index_rows(self._player_rows, by_name=True)

        features: list[ProspectFeatures] = []
        for draft_row in self._draft_rows:
            position = str(_row_value(draft_row, "position", "pos") or "").upper()
            if position not in target_positions:
                continue
            draft_year = _as_int(_row_value(draft_row, "season", "year", "draft_year"))
            if draft_year is None or draft_year < HISTORICAL_START_YEAR or draft_year > current_class_year:
                continue

            player_id = str(
                _row_value(
                    draft_row,
                    "player_id",
                    "gsis_id",
                    "pfr_id",
                    "sleeper_id",
                    "id",
                )
                or ""
            ).strip()
            player_name = str(
                _row_value(
                    draft_row,
                    "player_name",
                    "pfr_player_name",
                    "full_name",
                    "name",
                    "display_name",
                )
                or ""
            ).strip()
            if not player_id and not player_name:
                continue
            player_row = players_by_id.get(player_id) or players_by_name.get(player_name.lower()) or {}
            combine_row = combine_by_id.get(player_id) or combine_by_name.get(player_name.lower()) or {}

            if not player_id:
                player_id = str(
                    _row_value(player_row, "player_id", "gsis_id", "sleeper_id", "id") or player_name
                )
            if not player_name:
                player_name = str(
                    _row_value(player_row, "full_name", "player_name", "display_name", "name") or player_id
                )

            birth_date = _parse_birth_date(_row_value(player_row, "birth_date"))
            age_at_draft = _as_float(_row_value(player_row, "age"))
            if age_at_draft is None and birth_date is not None:
                age_at_draft = round((date(draft_year, 4, 1) - birth_date).days / 365.25, 2)

            features.append(
                ProspectFeatures(
                    player_id=player_id,
                    player_name=player_name,
                    position=position,
                    draft_year=draft_year,
                    age_at_draft=age_at_draft,
                    draft_ovr=_as_int(_row_value(draft_row, "pick", "overall_pick", "draft_pick")),
                    forty=_as_float(_row_value(combine_row, "forty", "forty_time")),
                    weight=_as_float(_row_value(combine_row, "weight", "weight_lb")),
                    height=_as_float(_row_value(combine_row, "height", "height_in")),
                    vertical=_as_float(_row_value(combine_row, "vertical")),
                    bench=_as_int(_row_value(combine_row, "bench", "bench_reps")),
                    cone=_as_float(_row_value(combine_row, "cone", "three_cone")),
                    shuttle=_as_float(_row_value(combine_row, "shuttle", "short_shuttle")),
                    **derive_college_profile(player_row, position),
                    adp=self._adp_lookup.get(player_id),
                )
            )
        return features

    def build_finish_rank_lookup(self) -> dict[str, list[int]]:
        totals: dict[tuple[str, str, int], float] = defaultdict(float)
        name_by_player_id: dict[str, str] = {}
        for row in self._weekly_rows:
            player_id = str(_row_value(row, "player_id") or "")
            position = str(_row_value(row, "position") or "").upper()
            season = _as_int(_row_value(row, "season"))
            fantasy_points = _as_float(_row_value(row, "fantasy_points")) or 0.0
            player_name = _normalize_name(_row_value(row, "player_name"))
            if not player_id or position not in POSITIONS or season is None:
                continue
            totals[(position, player_id, season)] += fantasy_points
            if player_name:
                name_by_player_id[player_id] = player_name

        by_position_season: dict[tuple[str, int], list[tuple[str, float]]] = defaultdict(list)
        for (position, player_id, season), total in totals.items():
            by_position_season[(position, season)].append((player_id, total))

        per_player: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for (position, season), rows in by_position_season.items():
            ordered = sorted(rows, key=lambda item: (-item[1], item[0]))
            for index, (player_id, _points) in enumerate(ordered, start=1):
                per_player[player_id].append((season, index))

        lookup: dict[str, list[int]] = {}
        for player_id, entries in per_player.items():
            ranks = [rank for _season, rank in sorted(entries)]
            lookup[player_id] = ranks
            player_name = name_by_player_id.get(player_id)
            if player_name and player_name not in lookup:
                lookup[player_name] = ranks
        return lookup

    def _index_rows(self, rows: list[dict[str, Any]], by_name: bool = False) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for row in rows:
            if by_name:
                key = str(
                    _row_value(row, "player_name", "full_name", "display_name", "name") or ""
                ).strip().lower()
            else:
                key = str(
                    _row_value(row, "player_id", "gsis_id", "pfr_id", "sleeper_id", "id") or ""
                ).strip()
            if key and key not in index:
                index[key] = row
        return index

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import polars as pl

from fantasy.ingestion.nfl_data_loader import NflDataPyLoader
from fantasy.prospects.archetype_clusterer import ArchetypeClusterer
from fantasy.prospects.comp_finder import CompFinder
from fantasy.prospects.constants import (
    DEFAULT_LEAGUE_ID,
    HISTORICAL_START_YEAR,
    HIT_RATE_HIGH,
    HIT_RATE_LOW,
    HIT_RATE_MODERATE,
    MIN_OUTCOME_SEASONS,
    OUTCOME_BUST,
    POSITIONS,
)
from fantasy.prospects.divergence_engine import DivergenceEngine
from fantasy.prospects.feature_builder import FeatureBuilder, derive_college_profile
from fantasy.prospects.hit_classifier import HitClassifier
from fantasy.prospects.models import ProspectFeatures, ProspectModelOutput
from fantasy.prospects.nflreadpy_loader import NflReadPyLoader
from fantasy.prospects.prospect_model import ProspectModel
from fantasy.prospects.prospect_repo import ProspectRepo

logger = logging.getLogger(__name__)


def run_pipeline(
    db_path: str,
    positions: list[str] | None = None,
    current_class_year: int = 2026,
    mode: str = "post_draft",
    pre_draft_csv: str | None = None,
) -> dict[str, Any]:
    selected_positions = [position for position in (positions or POSITIONS) if position in POSITIONS]
    if mode not in {"post_draft", "pre_draft"}:
        raise ValueError(f"Unsupported pipeline mode: {mode}")
    repo: ProspectRepo
    processed_outputs: list[ProspectModelOutput] = []
    feature_count = 0
    comp_count = 0
    flag_count = 0

    with duckdb.connect(db_path) as conn:
        repo = ProspectRepo(conn)
        scoring_class_year = current_class_year
        finish_rank_lookup: dict[str, list[int]] = {}
        persisted_history_by_position: dict[str, list[ProspectFeatures]] = {}
        current_features_by_position: dict[str, list[ProspectFeatures]] = {position: [] for position in selected_positions}

        if mode == "post_draft":
            loader = NflReadPyLoader()
            combine_df = loader.load_combine(HISTORICAL_START_YEAR, current_class_year + 1)
            players_df = loader.load_players()
            draft_df = loader.load_draft_picks(HISTORICAL_START_YEAR, current_class_year + 1)
            scoring_class_year = _resolve_current_class_year(draft_df, current_class_year)
            weekly_stats_df = _load_phase8_weekly_stats(conn, scoring_class_year)
            adp_lookup = _read_adp_baseline_from_db(conn)

            builder = FeatureBuilder(
                combine_df=combine_df,
                players_df=players_df,
                draft_df=draft_df,
                weekly_stats_df=weekly_stats_df,
                adp_lookup=adp_lookup,
            )
            finish_rank_lookup = builder.build_finish_rank_lookup()
            historical_build_year = scoring_class_year
            all_features = builder.build_all_features(
                current_class_year=historical_build_year,
                positions=selected_positions,
            )
            feature_count = len(all_features)
        else:
            pre_draft_features = _load_pre_draft_features(
                csv_path=pre_draft_csv,
                current_class_year=scoring_class_year,
                positions=selected_positions,
            )
            for position in selected_positions:
                persisted_history_by_position[position] = [
                    feature
                    for feature in repo.get_features_by_position(position, max_draft_year=scoring_class_year - 1)
                    if feature.outcome_bucket is not None
                ]
                current_features_by_position[position] = [
                    feature for feature in pre_draft_features if feature.position == position
                ]
            feature_count = len(pre_draft_features) + sum(len(rows) for rows in persisted_history_by_position.values())

        classifier = HitClassifier()
        divergence_engine = DivergenceEngine()
        comp_finder = CompFinder()
        computed_at = datetime.now(timezone.utc)

        persisted_features: list[ProspectFeatures] = []
        for position in selected_positions:
            if mode == "pre_draft":
                labeled_history = persisted_history_by_position.get(position, [])
                current_records = current_features_by_position.get(position, [])
                persisted_features.extend(current_records)
                if not labeled_history or not current_records:
                    logger.info("No persisted history or pre-draft records for %s", position)
                    continue
            else:
                position_features = [feature for feature in all_features if feature.position == position]
                if not position_features:
                    logger.info("No features built for %s", position)
                    continue

                historical_records: list[dict[str, Any]] = []
                current_records = []
                for feature in position_features:
                    ranks = finish_rank_lookup.get(feature.player_id) or finish_rank_lookup.get(
                        _normalize_name(feature.player_name)
                    ) or []
                    if feature.draft_year == scoring_class_year:
                        current_records.append(feature)
                        continue
                    historical_records.append(
                        {
                            **feature.model_dump(mode="python"),
                            "season_finish_ranks": ranks,
                        }
                    )

                labeled_history = [
                    ProspectFeatures.model_validate(row)
                    for row in classifier.classify_cohort(historical_records)
                    if row.get("outcome_bucket") is not None
                ]
                persisted_features.extend(labeled_history)
                persisted_features.extend(current_records)
                if not labeled_history or not current_records:
                    continue

            history_rows = [row.model_dump(mode="python") for row in labeled_history]
            history_df = pl.DataFrame(history_rows)
            model = ProspectModel(position)
            validation = model.walk_forward_validate(history_df)
            logger.info("Phase 8 %s validation: %s", position, validation)
            y_history = np.array(history_df["outcome_bucket"].to_list(), dtype=object)
            if len(set(y_history.tolist())) < 2:
                continue
            model.train_frame(history_df)

            clusterer = ArchetypeClusterer(position)
            clusterer.fit(history_rows)
            history_labels = clusterer.predict(history_rows)
            for index, row in enumerate(labeled_history):
                row.archetype_label = history_labels[index]
            current_rows = [row.model_dump(mode="python") for row in current_records]
            current_labels = clusterer.predict(current_rows)
            for index, row in enumerate(current_records):
                row.archetype_label = current_labels[index]
            archetype_rates = clusterer.get_archetype_hit_rates([row.model_dump(mode="python") for row in labeled_history])

            current_df = pl.DataFrame(current_rows)
            probabilities = model.predict_frame(current_df)
            scored = []
            for feature, probability in zip(current_records, probabilities, strict=False):
                score = probability.get("hit", 0.0) * 2.0 + probability.get("mediocre", 0.0)
                scored.append((feature, probability, score))
            scored.sort(key=lambda item: (-item[2], item[0].adp or 999.0, item[0].player_name))
            model_rankings = [item[0].player_id for item in scored]
            adp_rankings = [
                feature.player_id
                for feature in sorted(
                    current_records,
                    key=lambda item: (item.adp if item.adp is not None else 999.0, item.player_name),
                )
            ]

            for index, (feature, probability, _score) in enumerate(scored, start=1):
                comps, low_confidence = comp_finder.find_comps(feature, labeled_history)
                comp_features = [row for row in labeled_history if row.player_id in {comp.player_id for comp in comps}]
                sub_flags = divergence_engine.compute_sub_flags(feature, comp_features)
                direction, magnitude = divergence_engine.compute_divergence(
                    player_id=feature.player_id,
                    model_rankings=model_rankings,
                    adp_rankings=adp_rankings,
                    low_confidence=low_confidence,
                )
                predicted_bucket = max(probability.items(), key=lambda item: item[1])[0]
                output = ProspectModelOutput(
                    league_id=DEFAULT_LEAGUE_ID,
                    draft_season=scoring_class_year,
                    player_id=feature.player_id,
                    player_name=feature.player_name,
                    position=feature.position,
                    archetype_label=feature.archetype_label or "Unclassified",
                    hit_rate_bucket=_determine_hit_rate_bucket(archetype_rates, feature.archetype_label or "Unclassified"),
                    tier=_tier_from_rank(index),
                    predicted_tier=_tier_from_rank(index),
                    predicted_bucket=predicted_bucket,
                    risk_band=_risk_band(probability.get("bust", 0.0)),
                    comps=comps,
                    overvalue_flag_direction=direction,
                    overvalue_magnitude=magnitude,
                    low_confidence=low_confidence,
                    sub_flags=sub_flags,
                    computed_at=computed_at,
                )
                processed_outputs.append(output)
                comp_count += len(comps)
                flag_count += len(sub_flags)

        repo.upsert_features(persisted_features)
        repo.upsert_model_outputs(processed_outputs)
        league_ids = repo.get_league_ids()
        if league_ids:
            league_outputs = []
            for league_id in league_ids:
                for output in processed_outputs:
                    league_outputs.append(output.model_copy(update={"league_id": league_id}))
            repo.upsert_model_outputs(league_outputs)
            for output in league_outputs:
                repo.upsert_sub_flags(output.league_id, output.player_id, output.sub_flags)
        for output in processed_outputs:
            repo.upsert_sub_flags(output.league_id, output.player_id, output.sub_flags)

    return {
        "mode": mode,
        "scoring_class_year": scoring_class_year,
        "positions_processed": selected_positions,
        "features_built": feature_count,
        "prospects_scored": len(processed_outputs),
        "comps_generated": comp_count,
        "flags_generated": flag_count,
        "min_outcome_seasons": MIN_OUTCOME_SEASONS,
    }


def _tier_from_rank(rank: int) -> int:
    if rank <= 3:
        return 1
    if rank <= 8:
        return 2
    if rank <= 14:
        return 3
    return 4


def _risk_band(bust_probability: float) -> str:
    if bust_probability >= 0.6:
        return "High"
    if bust_probability >= 0.3:
        return "Moderate"
    return "Low"


def _determine_hit_rate_bucket(archetype_hit_rates: dict[str, dict[str, float]], archetype_label: str) -> str:
    hit_rate = archetype_hit_rates.get(archetype_label, {}).get("hit", 0.0)
    if hit_rate >= 0.4:
        return HIT_RATE_HIGH
    if hit_rate >= 0.2:
        return HIT_RATE_MODERATE
    return HIT_RATE_LOW


def _resolve_current_class_year(draft_df: pl.DataFrame, requested_year: int) -> int:
    if draft_df.is_empty() or "season" not in draft_df.columns:
        return requested_year
    available_years = sorted(
        {
            int(value)
            for value in draft_df["season"].drop_nulls().to_list()
        }
    )
    if not available_years:
        return requested_year
    if requested_year in available_years:
        return requested_year
    latest_year = available_years[-1]
    logger.info(
        "Requested current class year %s is not available in draft data; using latest available year %s.",
        requested_year,
        latest_year,
    )
    return latest_year


def _load_pre_draft_features(
    csv_path: str | None,
    current_class_year: int,
    positions: list[str],
) -> list[ProspectFeatures]:
    if not csv_path:
        raise ValueError("pre_draft mode requires --pre-draft-csv")
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Pre-draft prospect CSV not found: {path}")

    pre_draft_df = _read_pre_draft_csv_with_enrichment(path)
    missing_columns = sorted({"player_name", "position"} - set(pre_draft_df.columns))
    if missing_columns:
        raise ValueError(f"Pre-draft prospect CSV is missing required columns: {', '.join(missing_columns)}")

    features: list[ProspectFeatures] = []
    for row in pre_draft_df.to_dicts():
        position = str(row.get("position") or "").upper()
        if position not in positions:
            continue

        player_name = str(row.get("player_name") or "").strip()
        if not player_name:
            continue

        normalized_name = _normalize_name(player_name)
        draft_ovr = _safe_int(row.get("expected_draft_ovr"))
        if draft_ovr is None:
            draft_ovr = _safe_int(row.get("draft_ovr"))
        adp = _safe_float(row.get("adp"))
        if adp is None and draft_ovr is not None:
            adp = float(draft_ovr)

        features.append(
            ProspectFeatures(
                player_id=str(row.get("player_id") or f"pre_{current_class_year}_{normalized_name}"),
                player_name=player_name,
                position=position,
                draft_year=current_class_year,
                age_at_draft=_safe_float(row.get("age_at_draft")),
                draft_ovr=draft_ovr,
                forty=_safe_float(row.get("forty")),
                weight=_safe_float(row.get("weight")),
                height=_safe_float(row.get("height")),
                vertical=_safe_float(row.get("vertical")),
                bench=_safe_int(row.get("bench")),
                cone=_safe_float(row.get("cone")),
                shuttle=_safe_float(row.get("shuttle")),
                **derive_college_profile(row, position),
                adp=adp,
            )
        )
    return features


def _read_pre_draft_csv_with_enrichment(path: Path) -> pl.DataFrame:
    pre_draft_df = pl.read_csv(path)
    enrichment_path = path.with_name(f"{path.stem}.enrichment{path.suffix}")
    if not enrichment_path.exists():
        return pre_draft_df

    enrichment_df = pl.read_csv(enrichment_path)
    if "player_name" not in enrichment_df.columns:
        raise ValueError(
            f"Pre-draft enrichment CSV is missing required columns: player_name ({enrichment_path})"
        )

    join_keys = ["player_name"]
    if "position" in pre_draft_df.columns and "position" in enrichment_df.columns:
        join_keys.append("position")

    merged = pre_draft_df.join(enrichment_df, on=join_keys, how="left", suffix="_enrichment")
    overlapping = set(pre_draft_df.columns).intersection(enrichment_df.columns) - set(join_keys)
    for column in overlapping:
        enrichment_column = f"{column}_enrichment"
        if enrichment_column in merged.columns:
            merged = merged.with_columns(
                pl.coalesce(pl.col(enrichment_column), pl.col(column)).alias(column)
            ).drop(enrichment_column)
    return merged


def _load_phase8_weekly_stats(
    conn: duckdb.DuckDBPyConnection,
    current_class_year: int,
) -> pl.DataFrame:
    db_stats = _read_weekly_stats_from_db(conn)
    historical_years = list(range(HISTORICAL_START_YEAR, current_class_year))
    loader = NflDataPyLoader()
    historical_stats = loader.load_weekly_stats(historical_years) if historical_years else pl.DataFrame()
    if db_stats.is_empty():
        return historical_stats
    if historical_stats.is_empty():
        return db_stats
    return pl.concat([historical_stats, db_stats], how="diagonal_relaxed").unique(
        subset=["player_id", "season", "week"],
        keep="first",
    )


def _normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _read_weekly_stats_from_db(conn: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    try:
        rows = conn.execute(
            """
            SELECT player_id, season, week, fantasy_points, position
            FROM player_stats_weekly
            WHERE position IN ('QB', 'RB', 'WR', 'TE')
            """
        ).fetchall()
        return pl.DataFrame(
            rows,
            schema=["player_id", "season", "week", "fantasy_points", "position"],
            orient="row",
        )
    except duckdb.Error:
        return pl.DataFrame(
            schema={
                "player_id": pl.String,
                "season": pl.Int64,
                "week": pl.Int64,
                "fantasy_points": pl.Float64,
                "position": pl.String,
            }
        )


def _read_adp_baseline_from_db(conn: duckdb.DuckDBPyConnection) -> dict[str, float]:
    try:
        rows = conn.execute(
            """
            SELECT player_id, adp
            FROM player_adp_baseline
            WHERE player_id IS NOT NULL AND adp IS NOT NULL
            """
        ).fetchall()
    except duckdb.Error:
        return {}
    return {str(player_id): float(adp) for player_id, adp in rows}


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run prospect model pipeline")
    parser.add_argument("--db-path", required=True, help="Path to DuckDB database")
    parser.add_argument("--positions", default="QB,RB,WR,TE", help="Comma-separated positions")
    parser.add_argument("--current-class-year", type=int, default=2026, help="Current draft class year")
    parser.add_argument(
        "--mode",
        choices=("post_draft", "pre_draft"),
        default="post_draft",
        help="Score the drafted class or load an upcoming class from CSV.",
    )
    parser.add_argument(
        "--pre-draft-csv",
        default=None,
        help="CSV path for pre-draft scoring mode.",
    )
    args = parser.parse_args()
    result = run_pipeline(
        db_path=args.db_path,
        positions=[item.strip().upper() for item in args.positions.split(",") if item.strip()],
        current_class_year=args.current_class_year,
        mode=args.mode,
        pre_draft_csv=args.pre_draft_csv,
    )
    print(f"Pipeline complete: {result}")

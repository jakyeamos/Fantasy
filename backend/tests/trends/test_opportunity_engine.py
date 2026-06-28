from datetime import datetime, timezone

from fantasy.context.context_repo import ContextRepo
from fantasy.lineup.lineup_repo import LineupRepo
from fantasy.lineup.models import LineupResult, LineupSlotScore
from fantasy.trends import opportunity_engine
from fantasy.trends.constants import COMPONENT_COLS
from fantasy.trends.opportunity_engine import OpportunityEngine
from fantasy.trends.trend_repo import TrendRepo


class _StubCalendarService:
    def __init__(self, state: str) -> None:
        self._state = state

    def active_state(self, _league_id: str) -> str:
        return self._state


FRESH_NOW = datetime(2026, 6, 28, 12, tzinfo=timezone.utc)


def _components(score: float, *, fragility: float | None = None) -> dict[str, float]:
    values = {column: score for column in COMPONENT_COLS}
    values["comp_fragility"] = fragility if fragility is not None else max(0.0, min(1.0, 1.0 - score))
    return values


def _seed_league(conn, league_id: str) -> None:
    conn.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions, settings_blob, superflex, tep, ppr
        )
        VALUES (?, ?, '2025', '{}', '[]', '{}', FALSE, FALSE, 0.5)
        """,
        [league_id, league_id],
    )


def _seed_roster(conn, league_id: str, roster_id: int, owner_id: str, players: list[str]) -> None:
    conn.execute(
        """
        INSERT INTO rosters (
            id, league_id, roster_id, owner_id, owner_display_name, starters, players, reserve, taxi
        )
        VALUES (?, ?, ?, ?, ?, '[]', ?, '[]', '[]')
        """,
        [int(f"{1 if league_id == 'league_a' else 2}{roster_id}"), league_id, roster_id, owner_id, owner_id, str(players).replace("'", '"')],
    )


def _seed_direction(conn, league_id: str, roster_id: int, label: str) -> None:
    conn.execute(
        """
        INSERT INTO team_directions (
            id, league_id, roster_id, primary_label, confidence, reasoning,
            alternates_json, delta_json, approved_moves, discouraged_moves
        )
        VALUES (?, ?, ?, ?, 0.92, 'seed', '[]', '{}', '[]', '[]')
        """,
        [int(f"{1 if league_id == 'league_a' else 2}{roster_id}"), league_id, roster_id, label],
    )


def _seed_lineup_gap(conn, league_id: str, roster_id: int, position: str) -> None:
    LineupRepo(conn).save_lineup_result(
        LineupResult(
            league_id=league_id,
            roster_id=roster_id,
            slot_scores=[
                LineupSlotScore(
                    position=position,
                    player_id=f"weak_{position.lower()}",
                    player_name=f"Weak {position}",
                    starter_value=42.0,
                    replacement_level=35.0,
                    score=0.35,
                    playoff_target=49.0,
                    title_target=56.0,
                    elite_target=63.0,
                    upgrade_leverage_score=0.9,
                    gap_to_playoff_target=7.0,
                    gap_to_title_target=14.0,
                    gap_to_elite_target=21.0,
                    below_playoff_target=True,
                    below_title_target=True,
                    below_elite_target=True,
                    weak_relative_to_contender=True,
                    benchmark_used=True,
                    benchmark_sample_size=12,
                )
            ],
            total_lineup_score=42.0,
            overall_playoff_target=49.0,
            overall_title_target=56.0,
            overall_elite_target=63.0,
            overall_gap_to_playoff_target=7.0,
            overall_gap_to_title_target=14.0,
            overall_gap_to_elite_target=21.0,
            title_window_label="Fading Window",
            title_window_composite=0.45,
            ceiling_score=0.4,
            stability_score=0.3,
            depth_score=0.2,
        )
    )


def _seed_player(conn, player_id: str, name: str, position: str, age: int, adp: float) -> None:
    conn.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES (?, ?, ?, 'X', ?, '{}')
        """,
        [player_id, name, position, age],
    )
    conn.execute(
        """
        INSERT INTO player_adp_baseline (player_id, player_name, position, adp, adp_source)
        VALUES (?, ?, ?, ?, 'test')
        """,
        [player_id, name, position, adp],
    )


def _seed_trend_history(
    conn,
    *,
    player_id: str,
    current_score: float,
    prior_score: float,
    current_adp: float,
    prior_adp: float,
    prior_backfilled: bool = False,
) -> None:
    repo = TrendRepo(conn)
    repo.write_trend_row(
        player_id=player_id,
        season=2023,
        trend_label=None,
        confidence=None,
        delta_magnitude=0.0,
        adp_delta=None,
        components=_components(prior_score),
        startup_adp=prior_adp,
        backfilled=prior_backfilled,
    )
    repo.write_trend_row(
        player_id=player_id,
        season=2024,
        trend_label=None,
        confidence=None,
        delta_magnitude=0.0,
        adp_delta=None,
        components=_components(current_score),
        startup_adp=current_adp,
        backfilled=False,
    )


def _base_feed_db(db):
    _seed_league(db, "league_a")
    _seed_league(db, "league_b")
    _seed_roster(db, "league_a", 1, "user_self", ["player_x"])
    _seed_roster(db, "league_a", 2, "user_other", ["player_sell"])
    _seed_roster(db, "league_b", 1, "user_self", ["player_x"])
    _seed_roster(db, "league_b", 2, "user_other_b", [])
    _seed_direction(db, "league_a", 1, "true_contender")
    _seed_direction(db, "league_b", 1, "retool")
    return db


def test_feed_sorted_by_impact_score(db):
    conn = _base_feed_db(db)
    _seed_player(conn, "player_a", "Player A", "WR", 24, 52.5)
    _seed_player(conn, "player_b", "Player B", "WR", 24, 62.5)
    _seed_trend_history(conn, player_id="player_a", current_score=0.90, prior_score=0.30, current_adp=52.5, prior_adp=88.0)
    _seed_trend_history(
        conn,
        player_id="player_b",
        current_score=0.90,
        prior_score=0.30,
        current_adp=62.5,
        prior_adp=100.0,
        prior_backfilled=True,
    )

    items = OpportunityEngine(
        conn,
        calendar_service=_StubCalendarService("early_season"),
    ).build_feed()

    assert items[0].player_id == "player_a"


def test_feed_deduplicates_players(db):
    conn = _base_feed_db(db)
    _seed_player(conn, "player_x", "Player X", "WR", 25, 70.0)
    _seed_trend_history(conn, player_id="player_x", current_score=0.82, prior_score=0.40, current_adp=70.0, prior_adp=105.0)

    items = OpportunityEngine(conn, calendar_service=_StubCalendarService("early_season")).build_feed()
    rows = [item for item in items if item.player_id == "player_x"]

    assert len(rows) == 1
    assert set(rows[0].owned_in_leagues) == {"league_a", "league_b"}


def test_feed_buy_target_no_symbol(db):
    conn = _base_feed_db(db)
    _seed_player(conn, "player_y", "Player Y", "WR", 24, 74.0)
    _seed_trend_history(conn, player_id="player_y", current_score=0.86, prior_score=0.40, current_adp=74.0, prior_adp=102.0)

    items = OpportunityEngine(conn, calendar_service=_StubCalendarService("early_season")).build_feed()
    row = next(item for item in items if item.player_id == "player_y")

    assert row.owned_in_leagues == []


def test_suggested_action_sell(db):
    conn = _base_feed_db(db)
    _seed_player(conn, "player_sell", "Player Sell", "WR", 30, 70.0)
    _seed_trend_history(conn, player_id="player_sell", current_score=0.50, prior_score=0.90, current_adp=70.0, prior_adp=34.0)

    items = OpportunityEngine(conn, calendar_service=_StubCalendarService("early_season")).build_feed()
    row = next(item for item in items if item.player_id == "player_sell")

    assert row.adp_gap > 0
    assert row.suggested_action == "sell"


def test_owned_sell_opportunity_links_trade_evaluator_send_side(db):
    conn = _base_feed_db(db)
    _seed_player(conn, "player_x", "Player X", "WR", 30, 70.0)
    _seed_trend_history(
        conn,
        player_id="player_x",
        current_score=0.50,
        prior_score=0.90,
        current_adp=70.0,
        prior_adp=34.0,
    )

    items = OpportunityEngine(
        conn,
        calendar_service=_StubCalendarService("early_season"),
    ).build_feed()
    row = next(item for item in items if item.player_id == "player_x")

    assert row.suggested_action == "sell"
    assert row.cta is not None
    assert row.cta.destination == "trade_evaluator"
    assert row.cta.league_id == "league_a"
    assert row.cta.user_roster_id == 1
    assert row.cta.target_player_roster_id == 1


def test_suggested_action_buy(db):
    conn = _base_feed_db(db)
    _seed_player(conn, "player_buy", "Player Buy", "WR", 24, 80.0)
    _seed_trend_history(
        conn,
        player_id="player_buy",
        current_score=0.88,
        prior_score=0.45,
        current_adp=80.0,
        prior_adp=112.0,
    )

    items = OpportunityEngine(
        conn,
        calendar_service=_StubCalendarService("early_season"),
    ).build_feed()
    row = next(item for item in items if item.player_id == "player_buy")

    assert row.adp_gap < 0
    assert row.suggested_action == "buy"


def test_opponent_buy_opportunity_links_trade_evaluator_receive_side(db):
    conn = _base_feed_db(db)
    _seed_player(conn, "player_buy", "Player Buy", "WR", 24, 80.0)
    conn.execute(
        """
        UPDATE rosters
        SET players = '["player_buy"]'
        WHERE league_id = 'league_a' AND roster_id = 2
        """
    )
    _seed_trend_history(conn, player_id="player_buy", current_score=0.88, prior_score=0.45, current_adp=80.0, prior_adp=112.0)

    items = OpportunityEngine(conn, calendar_service=_StubCalendarService("early_season")).build_feed()
    row = next(item for item in items if item.player_id == "player_buy")

    assert row.suggested_action == "buy"
    assert row.cta is not None
    assert row.cta.destination == "trade_evaluator"
    assert row.cta.league_id == "league_a"
    assert row.cta.user_roster_id == 1
    assert row.cta.manager_roster_id == 2
    assert row.cta.target_player_roster_id == 2


def test_buy_target_solving_lineup_gap_outranks_larger_raw_gap(db):
    conn = _base_feed_db(db)
    conn.execute(
        """
        UPDATE rosters
        SET players = '["fit_wr","raw_rb"]'
        WHERE league_id = 'league_a' AND roster_id = 2
        """
    )
    _seed_lineup_gap(conn, "league_a", 1, "WR")
    for domain in ["usage", "stats", "schedule", "injuries"]:
        ContextRepo(conn).upsert_freshness(
            "league_a",
            domain,
            FRESH_NOW,
            f"test fresh {domain}",
        )
    _seed_player(conn, "fit_wr", "Fit WR", "WR", 24, 78.0)
    _seed_trend_history(
        conn,
        player_id="fit_wr",
        current_score=0.78,
        prior_score=0.45,
        current_adp=78.0,
        prior_adp=104.0,
    )
    _seed_player(conn, "raw_rb", "Raw RB", "RB", 24, 88.0)
    _seed_trend_history(
        conn,
        player_id="raw_rb",
        current_score=0.82,
        prior_score=0.45,
        current_adp=88.0,
        prior_adp=120.0,
    )

    items = OpportunityEngine(
        conn,
        calendar_service=_StubCalendarService("early_season"),
    ).build_feed()

    assert [item.player_id for item in items[:2]] == ["fit_wr", "raw_rb"]
    fit = items[0]
    raw = items[1]
    assert abs(raw.adp_gap) > abs(fit.adp_gap)
    assert fit.impact_score > raw.impact_score
    assert "current WR lineup gap" in fit.why_summary
    assert fit.weekly_fit is not None
    assert fit.weekly_fit.position == "WR"
    assert fit.weekly_fit.player_name == "Weak WR"
    assert fit.weekly_fit.gap_to_title_target == 14.0
    assert fit.weekly_fit.is_stale is False
    assert fit.weekly_fit.stale_domains == []


def test_stale_weekly_data_dampens_lineup_gap_opportunity_boost(db):
    conn = _base_feed_db(db)
    conn.execute(
        """
        UPDATE rosters
        SET players = '["fit_wr","raw_rb"]'
        WHERE league_id = 'league_a' AND roster_id = 2
        """
    )
    _seed_lineup_gap(conn, "league_a", 1, "WR")
    _seed_player(conn, "fit_wr", "Fit WR", "WR", 24, 78.0)
    _seed_trend_history(
        conn,
        player_id="fit_wr",
        current_score=0.78,
        prior_score=0.45,
        current_adp=78.0,
        prior_adp=104.0,
    )
    _seed_player(conn, "raw_rb", "Raw RB", "RB", 24, 88.0)
    _seed_trend_history(
        conn,
        player_id="raw_rb",
        current_score=0.82,
        prior_score=0.45,
        current_adp=88.0,
        prior_adp=120.0,
    )

    items = OpportunityEngine(
        conn,
        calendar_service=_StubCalendarService("early_season"),
    ).build_feed()

    assert [item.player_id for item in items[:2]] == ["raw_rb", "fit_wr"]
    fit = next(item for item in items if item.player_id == "fit_wr")
    assert "Verify stale weekly data first" in fit.why_summary
    assert fit.weekly_fit is not None
    assert fit.weekly_fit.is_stale is True
    assert set(fit.weekly_fit.stale_domains) == {"usage", "stats", "schedule", "injuries"}


def test_veteran_buy_low_contending_team(db):
    conn = _base_feed_db(db)
    _seed_player(conn, "player_vet", "Player Vet", "RB", 30, 120.0)
    _seed_trend_history(conn, player_id="player_vet", current_score=0.84, prior_score=0.96, current_adp=120.0, prior_adp=92.0)

    items = OpportunityEngine(conn, calendar_service=_StubCalendarService("early_season")).build_feed()
    row = next(item for item in items if item.player_id == "player_vet")

    assert row.adp_gap < 0
    assert row.suggested_action == "buy"


def test_low_confidence_not_suppressed(db):
    conn = _base_feed_db(db)
    _seed_player(conn, "player_low_conf", "Player Low Confidence", "WR", 25, 85.0)
    _seed_trend_history(
        conn,
        player_id="player_low_conf",
        current_score=0.86,
        prior_score=0.35,
        current_adp=85.0,
        prior_adp=130.0,
        prior_backfilled=True,
    )

    items = OpportunityEngine(conn, calendar_service=_StubCalendarService("early_season")).build_feed()

    assert any(item.player_id == "player_low_conf" for item in items)


def test_calendar_escalation_flag(db):
    conn = _base_feed_db(db)
    _seed_player(conn, "player_escalated", "Player Escalated", "WR", 24, 80.0)
    _seed_trend_history(conn, player_id="player_escalated", current_score=0.88, prior_score=0.45, current_adp=80.0, prior_adp=112.0)

    items = OpportunityEngine(conn, calendar_service=_StubCalendarService("post_combine")).build_feed()

    assert any(item.calendar_escalated for item in items)


def test_no_calendar_escalation(db):
    conn = _base_feed_db(db)
    _seed_player(conn, "player_normal", "Player Normal", "WR", 24, 80.0)
    _seed_trend_history(conn, player_id="player_normal", current_score=0.88, prior_score=0.45, current_adp=80.0, prior_adp=112.0)

    items = OpportunityEngine(conn, calendar_service=_StubCalendarService("early_season")).build_feed()

    assert all(item.calendar_escalated is False for item in items)


def test_feed_bounds_similarity_enrichment(db, monkeypatch):
    conn = _base_feed_db(db)
    for index in range(opportunity_engine.MAX_SIMILAR_PLAYER_ENRICHMENTS + 3):
        player_id = f"player_sim_{index}"
        _seed_player(conn, player_id, f"Player Sim {index}", "WR", 24, 70.0 + index)
        _seed_trend_history(
            conn,
            player_id=player_id,
            current_score=0.88,
            prior_score=0.45,
            current_adp=70.0 + index,
            prior_adp=112.0 + index,
        )

    enriched_player_ids: list[str] = []

    def _fake_similar_players(player_id, _snapshots):
        enriched_player_ids.append(str(player_id))
        return []

    monkeypatch.setattr(
        opportunity_engine,
        "find_similar_players_from_snapshots",
        _fake_similar_players,
    )

    items = OpportunityEngine(
        conn,
        calendar_service=_StubCalendarService("early_season"),
    ).build_feed()

    assert len(items) > opportunity_engine.MAX_SIMILAR_PLAYER_ENRICHMENTS
    assert len(enriched_player_ids) == opportunity_engine.MAX_SIMILAR_PLAYER_ENRICHMENTS
    assert enriched_player_ids == [
        item.player_id
        for item in items[: opportunity_engine.MAX_SIMILAR_PLAYER_ENRICHMENTS]
    ]


def test_feed_degrades_when_similarity_enrichment_fails(db, monkeypatch):
    conn = _base_feed_db(db)
    _seed_player(conn, "player_degraded", "Player Degraded", "WR", 24, 70.0)
    _seed_trend_history(
        conn,
        player_id="player_degraded",
        current_score=0.88,
        prior_score=0.45,
        current_adp=70.0,
        prior_adp=112.0,
    )

    def _raise_similarity(_player_id, _snapshots):
        raise RuntimeError("similarity unavailable")

    monkeypatch.setattr(
        opportunity_engine,
        "find_similar_players_from_snapshots",
        _raise_similarity,
    )

    engine = OpportunityEngine(
        conn,
        calendar_service=_StubCalendarService("early_season"),
    )
    items = engine.build_feed()

    assert items
    assert engine.degraded_reason is not None

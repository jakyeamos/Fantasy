"""Shared pytest fixtures.

Smoke-only quality-gate note: this module intentionally defines fixtures and
schema setup; assert statements live in the tests that consume them.
"""

import json
from datetime import datetime, timedelta

import duckdb
import pytest

from test_support.schema_sql import SCHEMA_SQL


@pytest.fixture
def db():
    conn = duckdb.connect(":memory:")
    for statement in SCHEMA_SQL:
        conn.execute(statement)
    yield conn
    conn.close()


@pytest.fixture
def mock_league_response():
    return {
        "league_id": "test_league_001",
        "name": "Test Dynasty League",
        "season": "2025",
        "scoring_settings": {
            "rec": 1.0,
            "rec_yd": 0.1,
            "rush_yd": 0.1,
            "pass_yd": 0.04,
            "pass_td": 4.0,
            "rec_td": 6.0,
            "rush_td": 6.0,
            "bonus_rec_te": 0.5,
        },
        "roster_positions": [
            "QB",
            "RB",
            "RB",
            "WR",
            "WR",
            "TE",
            "SUPER_FLEX",
            "BN",
            "BN",
            "BN",
            "BN",
            "BN",
            "BN",
        ],
        "settings": {"num_teams": 12, "taxi_slots": 4, "reserve_slots": 2},
    }


@pytest.fixture
def mock_roster_response():
    return {
        "roster_id": 1,
        "owner_id": "user_abc",
        "league_id": "test_league_001",
        "starters": ["4017", "4663"],
        "players": ["4017", "4663", "2374", "6945"],
        "reserve": ["5122"],
        "taxi": ["8888"],
        "settings": {
            "wins": 9,
            "losses": 4,
            "ties": 0,
            "fpts": 1534,
            "fpts_decimal": 5,
            "fpts_against": 1402.5,
            "waiver_position": 3,
            "waiver_budget_used": 27,
        },
    }


@pytest.fixture
def mock_traded_pick_response():
    return [
        {
            "season": "2025",
            "round": 1,
            "roster_id": 3,
            "owner_id": 7,
            "previous_owner_id": 3,
            "league_id": "test_league_001",
        },
        {
            "season": "2026",
            "round": 2,
            "roster_id": 5,
            "owner_id": 5,
            "previous_owner_id": None,
            "league_id": "test_league_001",
        },
    ]


@pytest.fixture
def mock_transaction_response():
    return [
        {
            "transaction_id": "txn_001",
            "type": "trade",
            "status": "complete",
            "created": 1700000000000,
            "roster_ids": [1, 3],
            "adds": {"4017": 3, "2374": 1},
            "drops": {"4017": 1, "2374": 3},
            "draft_picks": [{"season": "2025", "round": 1, "roster_id": 1, "owner_id": 3}],
            "leg": 1,
        },
        {
            "transaction_id": "txn_002",
            "type": "free_agent",
            "status": "complete",
            "created": 1700100000000,
            "roster_ids": [2],
            "adds": {"6945": 2},
            "drops": None,
            "draft_picks": [],
            "leg": 5,
        },
    ]


@pytest.fixture
def phase2_seed_data(db):
    db.execute(
        """
        INSERT INTO leagues (
            league_id, name, season, scoring_settings, roster_positions,
            settings_blob, superflex, tep, ppr
        )
        VALUES
            ('league_x', 'League X', '2025', '{"rec":1.0}', '["QB","RB","WR","TE","SUPER_FLEX","BN","BN"]', '{"num_teams":2}', TRUE, FALSE, 1.0)
        """
    )
    db.execute(
        """
        INSERT INTO rosters (id, league_id, roster_id, owner_id, starters, players, reserve, taxi)
        VALUES
            (1, 'league_x', 1, 'user_a', '["qb1","rb1","wr1","te1"]', '["qb1","rb1","wr1","te1","rbb1","wrb1"]', '[]', '[]'),
            (2, 'league_x', 2, 'user_b', '["qb2","rb2","wr2","te2"]', '["qb2","rb2","wr2","te2","rbb2","wrb2"]', '[]', '[]')
        """
    )
    db.execute(
        """
        INSERT INTO players (player_id, full_name, position, team, age, metadata_blob)
        VALUES
            ('qb1','QB One','QB','A',24,'{}'),
            ('rb1','RB One','RB','A',24,'{}'),
            ('wr1','WR One','WR','A',23,'{}'),
            ('te1','TE One','TE','A',25,'{}'),
            ('rbb1','RB Bench One','RB','A',22,'{}'),
            ('wrb1','WR Bench One','WR','A',22,'{}'),
            ('qb2','QB Two','QB','B',33,'{}'),
            ('rb2','RB Two','RB','B',29,'{}'),
            ('wr2','WR Two','WR','B',31,'{}'),
            ('te2','TE Two','TE','B',30,'{}'),
            ('rbb2','RB Bench Two','RB','B',28,'{}'),
            ('wrb2','WR Bench Two','WR','B',28,'{}'),
            ('rookie1','Rookie One','WR','C',21,'{}'),
            ('vet1','Vet One','RB','C',30,'{}')
        """
    )
    stats_rows = [
        ("qb1", "QB One", "QB", 2024, 1, 0, 0, 0, 0, 20, 1, 3, 250, 2, 0, 0, 0, 0, 22),
        ("rb1", "RB One", "RB", 2024, 1, 3, 4, 20, 0, 90, 1, 18, 0, 0, 0, 0, 0, 0, 20),
        ("wr1", "WR One", "WR", 2024, 1, 7, 8, 90, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 22),
        ("te1", "TE One", "TE", 2024, 1, 5, 6, 55, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 16),
        ("rbb1", "RB Bench One", "RB", 2024, 1, 2, 2, 10, 0, 40, 0, 8, 0, 0, 0, 0, 0, 0, 7),
        ("wrb1", "WR Bench One", "WR", 2024, 1, 3, 4, 40, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7),
        ("qb2", "QB Two", "QB", 2024, 1, 0, 0, 0, 0, 10, 0, 2, 200, 1, 1, 0, 0, 0, 14),
        ("rb2", "RB Two", "RB", 2024, 1, 1, 2, 5, 0, 50, 0, 12, 0, 0, 0, 0, 0, 0, 8),
        ("wr2", "WR Two", "WR", 2024, 1, 4, 6, 35, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7),
        ("te2", "TE Two", "TE", 2024, 1, 3, 4, 25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5),
        ("rbb2", "RB Bench Two", "RB", 2024, 1, 1, 1, 5, 0, 15, 0, 4, 0, 0, 0, 0, 0, 0, 3),
        ("wrb2", "WR Bench Two", "WR", 2024, 1, 1, 2, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3),
        ("rookie1", "Rookie One", "WR", 2024, 1, 2, 2, 18, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5),
        ("vet1", "Vet One", "RB", 2024, 1, 1, 1, 2, 0, 30, 0, 9, 0, 0, 0, 0, 0, 0, 5),
    ]
    db.executemany(
        """
        INSERT INTO player_stats_weekly (
            player_id, player_name, position, season, week, receptions, targets,
            receiving_yards, receiving_tds, rushing_yards, rushing_tds, carries,
            passing_yards, passing_tds, interceptions, passing_2pt_conversions,
            receiving_2pt_conversions, rushing_2pt_conversions, fantasy_points
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        stats_rows,
    )
    db.execute(
        """
        INSERT INTO player_adp_baseline (player_id, player_name, position, adp, adp_source)
        VALUES
            ('qb1','QB One','QB',30,'test'),
            ('rb1','RB One','RB',20,'test'),
            ('wr1','WR One','WR',10,'test'),
            ('te1','TE One','TE',45,'test'),
            ('rbb1','RB Bench One','RB',90,'test'),
            ('wrb1','WR Bench One','WR',110,'test'),
            ('qb2','QB Two','QB',85,'test'),
            ('rb2','RB Two','RB',95,'test'),
            ('wr2','WR Two','WR',120,'test'),
            ('te2','TE Two','TE',150,'test'),
            ('rbb2','RB Bench Two','RB',170,'test'),
            ('wrb2','WR Bench Two','WR',180,'test'),
            ('rookie1','Rookie One','WR',50,'test'),
            ('vet1','Vet One','RB',130,'test')
        """
    )
    db.execute(
        """
        INSERT INTO traded_picks (id, league_id, season, round, roster_id, owner_id, previous_owner_id)
        VALUES
            (1, 'league_x', '2025', 1, 2, '1', '2'),
            (2, 'league_x', '2026', 2, 2, '1', '2')
        """
    )
    return db


@pytest.fixture
def phase3_seed_data(phase2_seed_data):
    phase2_seed_data.execute(
        """
        INSERT INTO transactions (
            transaction_id, league_id, type, status, created_at,
            roster_ids, adds, drops, draft_picks, week
        )
        VALUES
            (
                'trade_1',
                'league_x',
                'trade',
                'complete',
                CURRENT_TIMESTAMP,
                '[1,2]',
                '{"wr2":1,"vet1":2}',
                '{"vet1":1,"wr2":2}',
                '[{"season":"2026","round":1,"roster_id":2,"owner_id":1,"previous_owner_id":2}]',
                5
            ),
            (
                'trade_2',
                'league_x',
                'trade',
                'complete',
                CURRENT_TIMESTAMP,
                '[1,2]',
                '{"rookie1":2,"wrb1":1}',
                '{"wrb1":2,"rookie1":1}',
                '[]',
                6
            )
        """
    )
    return phase2_seed_data


@pytest.fixture
def profiling_seed_data(phase2_seed_data):
    phase2_seed_data.execute("DELETE FROM transactions WHERE league_id = 'league_x'")
    phase2_seed_data.execute(
        """
        INSERT INTO team_directions (
            id, league_id, roster_id, primary_label, confidence, reasoning,
            alternates_json, delta_json, approved_moves, discouraged_moves
        )
        VALUES
            (
                1, 'league_x', 1, 'hard_rebuild', 0.92, 'seeded',
                '[]', '{}', '[]', '[]'
            ),
            (
                2, 'league_x', 2, 'true_contender', 0.88, 'seeded',
                '[]', '{}', '[]', '[]'
            )
        ON CONFLICT (league_id, roster_id) DO UPDATE SET
            primary_label = EXCLUDED.primary_label,
            confidence = EXCLUDED.confidence,
            reasoning = EXCLUDED.reasoning,
            alternates_json = EXCLUDED.alternates_json,
            delta_json = EXCLUDED.delta_json,
            approved_moves = EXCLUDED.approved_moves,
            discouraged_moves = EXCLUDED.discouraged_moves
        """
    )

    base_time = datetime(2025, 1, 1, 12, 0, 0)
    trade_rows = [
        ("prof_trade_1", "qb2", "wr1", 1, 4),
        ("prof_trade_2", "qb2", "rb1", 2, 5),
        ("prof_trade_3", "qb2", "rookie1", 1, 6),
        ("prof_trade_4", "qb2", "qb1", 0, 7),
        ("prof_trade_5", "qb2", "te1", 0, 8),
        ("prof_trade_6", "vet1", "wr1", 0, 9),
        ("prof_trade_7", "vet1", "rb1", 0, 10),
        ("prof_trade_8", "vet1", "rookie1", 0, 11),
        ("prof_trade_9", "wr2", "rbb1", 0, 12),
        ("prof_trade_10", "wr2", "wrb1", 0, 13),
        ("prof_trade_11", "wr2", "te1", 0, 14),
        ("prof_trade_12", "wr2", "wr1", 0, 15),
    ]
    for index, (transaction_id, received, sent, sent_pick_round, week) in enumerate(trade_rows):
        draft_picks = (
            [
                {
                    "season": "2026",
                    "round": sent_pick_round,
                    "roster_id": 2,
                    "owner_id": 2,
                    "previous_owner_id": 1,
                }
            ]
            if sent_pick_round
            else []
        )
        phase2_seed_data.execute(
            """
            INSERT INTO transactions (
                transaction_id, league_id, type, status, created_at,
                roster_ids, adds, drops, draft_picks, week
            )
            VALUES (?, 'league_x', 'trade', 'complete', ?, ?, ?, ?, ?, ?)
            """,
            [
                transaction_id,
                base_time + timedelta(days=index),
                json.dumps([1, 2]),
                json.dumps({received: 1, sent: 2}),
                json.dumps({received: 2, sent: 1}),
                json.dumps(draft_picks),
                week,
            ],
        )
    return phase2_seed_data


@pytest.fixture
def trade_seed_data(profiling_seed_data):
    from fantasy.intelligence.intelligence_service import IntelligenceService
    from fantasy.profiling.profiling_engine import ProfilingEngine
    from fantasy.profiling.profiling_repo import ProfilingRepo

    conn = profiling_seed_data
    IntelligenceService(conn).compute_league("league_x")
    conn.execute(
        """
        UPDATE team_directions
        SET primary_label = 'hard_rebuild', confidence = 0.92
        WHERE league_id = 'league_x' AND roster_id = 1
        """
    )

    engine = ProfilingEngine(conn)
    repo = ProfilingRepo(conn)
    for profile in engine.compute_all_profiles("league_x"):
        repo.upsert_profile(profile)
        repo.replace_pitch_angles(profile.league_id, profile.roster_id, profile.pitch_angles)
    return conn

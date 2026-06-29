import json

from fastapi.testclient import TestClient

from fantasy.main import create_app
from fantasy.routers.deps import get_read_db_conn


def _override_conn(conn):
    def _getter():
        yield conn

    return _getter


def _seed_draft_selection_rows(conn):
    conn.execute(
        """
        INSERT INTO draft_pick_selections (
            id, league_id, draft_id, roster_id, player_id, pick_slot,
            round_number, season, draft_type, position, archetype_label, ingested_at
        )
        VALUES
            (1, 'league_x', 'rookie_draft', 1, 'wr1', 1, 1, 2025, 'rookie', 'WR', 'separator', TIMESTAMP '2025-05-01 12:00:00'),
            (2, 'league_x', 'rookie_draft', 2, 'qb2', 2, 1, 2025, 'rookie', 'QB', 'pocket', TIMESTAMP '2025-05-01 12:00:00'),
            (3, 'league_x', 'startup_draft', 1, 'rb1', 1, 1, 2025, 'startup', 'RB', NULL, TIMESTAMP '2025-04-01 12:00:00')
        """
    )


def test_draft_grades_returns_rookie_and_startup_team_summaries(trade_seed_data):
    _seed_draft_selection_rows(trade_seed_data)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get("/draft-grades/league_x")

    assert response.status_code == 200
    payload = response.json()
    assert {item["draft_type"] for item in payload["selections"]} == {"rookie", "startup"}
    assert payload["team_summaries"]
    assert payload["best_value"] is not None
    assert payload["biggest_reach"] is not None


def test_rookie_grades_reward_model_value_and_tier_gap(trade_seed_data):
    trade_seed_data.execute("DELETE FROM draft_pick_selections WHERE league_id = 'league_x'")
    trade_seed_data.execute(
        """
        INSERT INTO draft_pick_selections (
            id, league_id, draft_id, roster_id, player_id, pick_slot,
            round_number, season, draft_type, position, archetype_label, ingested_at
        )
        VALUES
            (10, 'league_x', 'rookie_edge', 1, 'qb2', 1, 1, 2026, 'rookie', 'QB', 'pocket', TIMESTAMP '2026-05-01 12:00:00'),
            (11, 'league_x', 'rookie_edge', 2, 'wr1', 2, 1, 2026, 'rookie', 'WR', 'separator', TIMESTAMP '2026-05-01 12:00:00'),
            (12, 'league_x', 'rookie_edge', 1, 'rb1', 3, 1, 2026, 'rookie', 'RB', 'workhorse', TIMESTAMP '2026-05-01 12:00:00')
        """
    )
    trade_seed_data.execute(
        """
        UPDATE player_values
        SET lens_market = CASE player_id
            WHEN 'qb2' THEN 0.30
            WHEN 'wr1' THEN 0.82
            WHEN 'rb1' THEN 0.52
            ELSE lens_market
        END,
        lens_team_fit = CASE player_id
            WHEN 'qb2' THEN 0.00
            WHEN 'wr1' THEN 0.30
            WHEN 'rb1' THEN 0.10
            ELSE lens_team_fit
        END
        WHERE league_id = 'league_x'
        """
    )
    trade_seed_data.executemany(
        """
        INSERT INTO prospect_model_outputs (
            league_id, draft_season, player_id, player_name, position,
            archetype_label, hit_rate_bucket, tier, predicted_tier,
            predicted_bucket, risk_band, overvalue_flag_direction,
            overvalue_magnitude, low_confidence, comps_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (league_id, draft_season, player_id) DO UPDATE SET
            tier = EXCLUDED.tier,
            predicted_tier = EXCLUDED.predicted_tier,
            predicted_bucket = EXCLUDED.predicted_bucket,
            risk_band = EXCLUDED.risk_band,
            overvalue_flag_direction = EXCLUDED.overvalue_flag_direction,
            overvalue_magnitude = EXCLUDED.overvalue_magnitude,
            low_confidence = EXCLUDED.low_confidence
        """,
        [
            ("league_x", 2026, "qb2", "QB Two", "QB", "Pocket", "low", 4, 4, "miss", "High", "overvalued", 4, False, "[]"),
            ("league_x", 2026, "wr1", "WR One", "WR", "Separator", "high", 1, 1, "hit", "Low", "undervalued", 4, False, "[]"),
            ("league_x", 2026, "rb1", "RB One", "RB", "Workhorse", "mid", 2, 2, "hit", "Medium", None, None, False, "[]"),
        ],
    )
    trade_seed_data.executemany(
        """
        INSERT INTO historical_prospect_features (
            player_id, draft_year, position, player_name, age_at_draft, draft_ovr,
            college_rec_ypg, college_rush_ypg, college_yprr, college_ypt,
            college_ypc, college_ypa, college_pass_td_rate, college_qb_rush_ypg,
            college_scramble_rate, college_mkt_share_proxy, college_td_rate,
            college_completion_pct_proxy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (player_id, draft_year) DO UPDATE SET
            age_at_draft = EXCLUDED.age_at_draft,
            draft_ovr = EXCLUDED.draft_ovr,
            college_rec_ypg = EXCLUDED.college_rec_ypg,
            college_rush_ypg = EXCLUDED.college_rush_ypg,
            college_yprr = EXCLUDED.college_yprr,
            college_ypt = EXCLUDED.college_ypt,
            college_ypc = EXCLUDED.college_ypc,
            college_ypa = EXCLUDED.college_ypa,
            college_pass_td_rate = EXCLUDED.college_pass_td_rate,
            college_qb_rush_ypg = EXCLUDED.college_qb_rush_ypg,
            college_scramble_rate = EXCLUDED.college_scramble_rate,
            college_mkt_share_proxy = EXCLUDED.college_mkt_share_proxy,
            college_td_rate = EXCLUDED.college_td_rate,
            college_completion_pct_proxy = EXCLUDED.college_completion_pct_proxy
        """,
        [
            ("qb2", 2026, "QB", "QB Two", 23.8, 96, None, None, None, None, None, 6.5, 0.038, 4.0, 0.02, None, None, 0.58),
            ("wr1", 2026, "WR", "WR One", 21.1, 12, 94.0, None, 3.1, 11.2, None, None, None, None, None, 0.31, 0.14, None),
            ("rb1", 2026, "RB", "RB One", 21.5, 45, 18.0, 92.0, None, None, 5.8, None, None, None, None, 0.78, 0.11, None),
        ],
    )
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get("/draft-grades/league_x")

    assert response.status_code == 200
    payload = response.json()
    by_player = {item["player_id"]: item for item in payload["selections"]}
    assert by_player["wr1"]["grade_score"] > by_player["qb2"]["grade_score"]
    assert by_player["wr1"]["grade_label"] in {"A", "B"}
    assert "model steal" in by_player["wr1"]["rationale"]
    assert "model reach" in by_player["qb2"]["rationale"]
    assert "rookie feature profile" in by_player["wr1"]["rationale"]
    assert "draft capital 12" in by_player["wr1"]["rationale"]
    assert "YPRR 3.10" in by_player["wr1"]["rationale"]


def test_draft_grades_marks_at_time_available_from_prior_snapshot(trade_seed_data):
    _seed_draft_selection_rows(trade_seed_data)
    trade_seed_data.execute(
        """
        INSERT INTO league_snapshots (
            id, league_id, snapshot_at, snapshot_type, triggered_by, payload_json
        )
        VALUES (1, 'league_x', TIMESTAMP '2025-03-01 12:00:00', 'full', 'test', ?)
        """,
        [
            json.dumps(
                {
                    "state": {
                        "rosters": [
                            {
                                "roster_id": 1,
                                "player_values": [
                                    {"player_id": "rb1", "lens_market": 0.72},
                                    {"player_id": "wr1", "lens_market": 0.88},
                                ],
                            }
                        ]
                    }
                }
            )
        ],
    )
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get("/draft-grades/league_x")

    assert response.status_code == 200
    payload = response.json()
    rb_pick = next(item for item in payload["selections"] if item["player_id"] == "rb1")
    assert rb_pick["at_time"]["status"] == "available"
    assert rb_pick["at_time"]["value"] == 0.72


def test_draft_grades_marks_at_time_unavailable_without_snapshot(trade_seed_data):
    _seed_draft_selection_rows(trade_seed_data)
    app = create_app()
    app.dependency_overrides[get_read_db_conn] = _override_conn(trade_seed_data)
    client = TestClient(app)

    response = client.get("/draft-grades/league_x")

    assert response.status_code == 200
    payload = response.json()
    assert all(item["at_time"]["status"] == "unavailable" for item in payload["selections"])

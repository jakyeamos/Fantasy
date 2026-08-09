from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from fantasy.tools.db_baseline import copy_database, inventory


def test_inventory_records_row_counts_columns_and_stable_key_hints():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE leagues (league_id VARCHAR, name VARCHAR)")
    conn.execute("INSERT INTO leagues VALUES ('league_x', 'League X')")

    tables = inventory(conn)

    assert tables == [
        {
            "table": "leagues",
            "row_count": 1,
            "columns": ["league_id", "name"],
            "candidate_key": ["league_id"],
        }
    ]
    conn.close()


def test_copy_database_writes_manifest_without_mutating_source(tmp_path: Path):
    source = tmp_path / "source.duckdb"
    destination = tmp_path / "copies" / "baseline.duckdb"
    manifest_path = tmp_path / "manifests" / "baseline.json"
    conn = duckdb.connect(str(source))
    conn.execute("CREATE TABLE leagues (league_id VARCHAR, name VARCHAR)")
    conn.execute("INSERT INTO leagues VALUES ('league_x', 'League X')")
    conn.close()

    manifest = copy_database(
        source,
        destination,
        manifest_path=manifest_path,
    )

    assert destination.exists()
    assert manifest_path.exists()
    assert manifest["source_path"] == str(source.resolve())
    assert manifest["database_path"] == str(destination.resolve())
    assert manifest["table_count"] == 1
    assert manifest["tables"][0]["candidate_key"] == ["league_id"]
    assert json.loads(manifest_path.read_text()) == manifest
    with duckdb.connect(str(destination), read_only=True) as copied:
        assert copied.execute("SELECT COUNT(*) FROM leagues").fetchone() == (1,)


def test_copy_database_requires_explicit_force_for_existing_destination(tmp_path: Path):
    source = tmp_path / "source.duckdb"
    destination = tmp_path / "destination.duckdb"
    conn = duckdb.connect(str(source))
    conn.execute("CREATE TABLE leagues (league_id VARCHAR)")
    conn.close()
    destination.write_bytes(b"keep this disposable target")

    with pytest.raises(FileExistsError):
        copy_database(source, destination)


def test_copy_database_removes_stale_destination_wal_when_source_has_none(
    tmp_path: Path,
):
    source = tmp_path / "source.duckdb"
    destination = tmp_path / "destination.duckdb"
    conn = duckdb.connect(str(source))
    conn.execute("CREATE TABLE leagues (league_id VARCHAR)")
    conn.close()
    destination.write_bytes(b"old database")
    Path(f"{destination}.wal").write_bytes(b"old wal")

    copy_database(source, destination, force=True)

    assert not Path(f"{destination}.wal").exists()

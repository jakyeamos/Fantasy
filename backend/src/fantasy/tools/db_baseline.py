"""Copy a DuckDB database and record a stable inventory for v2 verification.

The tool never overwrites an existing destination unless ``--force`` is
provided. It is intended for disposable baseline copies, migration rehearsals,
and explicit restore operations; it does not mutate the source database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


KEY_HINTS: dict[str, tuple[str, ...]] = {
    "leagues": ("league_id",),
    "rosters": ("league_id", "roster_id"),
    "players": ("player_id",),
    "transactions": ("transaction_id", "league_id"),
    "league_snapshots": ("league_id", "snapshot_id"),
    "ingest_runs": ("league_id", "run_id"),
    "player_values": ("league_id", "roster_id", "player_id"),
    "team_scorecards": ("league_id", "roster_id"),
    "team_directions": ("league_id", "roster_id"),
}


def _wal_path(database_path: Path) -> Path:
    return Path(f"{database_path}.wal")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tables(conn: duckdb.DuckDBPyConnection) -> list[str]:
    rows = conn.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main' AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
    ).fetchall()
    return [str(row[0]) for row in rows]


def inventory(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Return row counts, columns, and stable key hints for every base table."""

    result: list[dict[str, Any]] = []
    for table_name in _tables(conn):
        columns = [
            str(row[0])
            for row in conn.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'main' AND table_name = ?
                ORDER BY ordinal_position
                """,
                [table_name],
            ).fetchall()
        ]
        quoted_table = '"' + table_name.replace('"', '""') + '"'
        row_count = int(conn.execute(f"SELECT COUNT(*) FROM {quoted_table}").fetchone()[0])
        candidate_key = [column for column in KEY_HINTS.get(table_name, ()) if column in columns]
        if not candidate_key:
            candidate_key = [column for column in ("id",) if column in columns]
        result.append(
            {
                "table": table_name,
                "row_count": row_count,
                "columns": columns,
                "candidate_key": candidate_key,
            }
        )
    return result


def _schema_version(conn: duckdb.DuckDBPyConnection) -> str | None:
    if "alembic_version" not in _tables(conn):
        return None
    row = conn.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
    return str(row[0]) if row else None


def build_manifest(database_path: Path, *, source_path: Path | None = None) -> dict[str, Any]:
    """Build a JSON-serializable manifest from a copied database."""

    with duckdb.connect(str(database_path), read_only=True) as conn:
        tables = inventory(conn)
        schema_version = _schema_version(conn)
    wal_path = _wal_path(database_path)
    return {
        "manifest_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_path": str(source_path) if source_path else None,
        "database_path": str(database_path),
        "database_sha256": _sha256(database_path),
        "wal_path": str(wal_path) if wal_path.exists() else None,
        "wal_sha256": _sha256(wal_path) if wal_path.exists() else None,
        "alembic_version": schema_version,
        "table_count": len(tables),
        "tables": tables,
    }


def _copy_file(source: Path, destination: Path, *, force: bool) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Database source does not exist: {source}")
    if destination.exists() and not force:
        raise FileExistsError(
            f"Destination already exists: {destination}; pass --force only for a disposable target"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    shutil.copy2(source, destination)


def copy_database(
    source: Path,
    destination: Path,
    *,
    manifest_path: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Copy a database and its adjacent WAL, then write an inventory manifest."""

    source = source.expanduser().resolve()
    destination = destination.expanduser().resolve()
    if source == destination:
        raise ValueError("Source and destination must be different paths")
    _copy_file(source, destination, force=force)

    source_wal = _wal_path(source)
    destination_wal = _wal_path(destination)
    if source_wal.exists():
        _copy_file(source_wal, destination_wal, force=True)
    elif destination_wal.exists():
        # A forced refresh must not leave an old WAL paired with the new copy.
        destination_wal.unlink()

    manifest = build_manifest(destination, source_path=source)
    target_manifest = manifest_path or Path(f"{destination}.manifest.json")
    target_manifest = target_manifest.expanduser().resolve()
    target_manifest.parent.mkdir(parents=True, exist_ok=True)
    target_manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def restore_database(
    backup: Path,
    destination: Path,
    *,
    manifest_path: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Restore a backup into an explicit target, requiring --force to overwrite."""

    return copy_database(
        backup,
        destination,
        manifest_path=manifest_path,
        force=force,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("copy", "restore"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--source", "--backup", required=True, dest="source")
        subparser.add_argument("--destination", required=True)
        subparser.add_argument("--manifest")
        subparser.add_argument("--force", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    manifest = copy_database(
        Path(args.source),
        Path(args.destination),
        manifest_path=Path(args.manifest) if args.manifest else None,
        force=args.force,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

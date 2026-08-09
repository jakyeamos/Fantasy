from __future__ import annotations

import argparse
import asyncio
import json
import sys

from fantasy.db.connection import close_connection, get_write_connection
from fantasy.intelligence.runner import FreshIntelligenceRunner


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m fantasy.intelligence")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Build the fresh intelligence morning brief")
    run.add_argument("--scheduled", action="store_true")
    run.add_argument("--source", action="append", default=[])
    run.add_argument("--league", action="append", default=[])
    return parser


async def _main() -> int:
    args = _parser().parse_args()
    conn = get_write_connection()
    try:
        tables = {str(row[0]) for row in conn.execute("SHOW TABLES").fetchall()}
        if "intelligence_source_runs" not in tables:
            print("Fresh Intelligence schema is missing. Run `uv run alembic upgrade head`.", file=sys.stderr)
            return 2
        result = await FreshIntelligenceRunner(conn).run(
            scheduled=args.scheduled,
            source_ids=args.source or None,
            league_ids=args.league or None,
        )
        print(json.dumps(result.model_dump(mode="json"), indent=2))
        return 0 if result.status != "failed" else 1
    finally:
        close_connection(conn)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))

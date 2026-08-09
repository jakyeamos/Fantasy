from __future__ import annotations

import argparse
import json

import duckdb

from fantasy.config import get_settings
from fantasy.decision.calibration import (
    DEFAULT_MINIMUM_SAMPLE_SIZE,
    run_decision_calibration,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Calibrate agent decision confidence from labeled outcome events."
    )
    parser.add_argument("--season", required=True)
    parser.add_argument(
        "--min-sample-size",
        type=int,
        default=DEFAULT_MINIMUM_SAMPLE_SIZE,
    )
    args = parser.parse_args(argv)

    conn = duckdb.connect(str(get_settings().db_path))
    try:
        result = run_decision_calibration(
            conn,
            season=args.season,
            min_sample_size=args.min_sample_size,
        )
    finally:
        conn.close()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "available" else 2


if __name__ == "__main__":
    raise SystemExit(main())

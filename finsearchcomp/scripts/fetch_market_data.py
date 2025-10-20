"""Standalone script to fetch and persist all configured market snapshots."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Dict

PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(PACKAGE_ROOT))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from finsearchcomp.data import save_universe_dataframes

DEFAULT_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "market_snapshots")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch all configured market universes and persist them to disk."
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to store snapshot files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--format",
        dest="file_format",
        choices=("csv", "json"),
        default="csv",
        help="File format for saved snapshots (default: csv).",
    )
    parser.add_argument(
        "--ttl",
        type=int,
        default=60,
        help="Cache TTL in seconds when reusing snapshots during a single run (default: 60).",
    )
    parser.add_argument(
        "--no-timestamp",
        action="store_true",
        help="Disable timestamp suffix in filenames (files will be overwritten each run).",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Ignore in-memory cache and force fresh downloads for every universe.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (default: INFO).",
    )
    return parser.parse_args()


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def main() -> None:
    args = parse_args()
    configure_logging(args.log_level)

    logging.info("Fetching market snapshots...")
    saved_paths: Dict[str, str] = save_universe_dataframes(
        output_dir=os.path.abspath(args.output_dir),
        ttl_sec=args.ttl,
        force_refresh=args.force_refresh,
        file_format=args.file_format,
        timestamped=not args.no_timestamp,
    )

    for universe, path in saved_paths.items():
        logging.info("Saved %s -> %s", universe, path)
    logging.info("Completed market snapshot refresh.")


if __name__ == "__main__":
    main()

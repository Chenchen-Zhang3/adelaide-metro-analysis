"""Run bounded or continuous Adelaide Metro GTFS-Realtime collection."""

import argparse
import logging
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Allow imports from the project root.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def parse_arguments():
    """Read command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Collect Adelaide Metro GTFS-Realtime data and persist it "
            "to the historical SQLite database."
        )
    )

    parser.add_argument(
        "--stop-times",
        required=True,
        type=Path,
        help="Path to the static GTFS stop_times.txt file.",
    )

    parser.add_argument(
        "--database",
        type=Path,
        help=(
            "Optional SQLite database path. "
            "Defaults to backend/database/adelaide_metro.db."
        ),
    )

    run_mode = parser.add_mutually_exclusive_group(required=True)

    run_mode.add_argument(
        "--cycles",
        type=int,
        help="Number of collection cycles to run.",
    )

    run_mode.add_argument(
        "--continuous",
        action="store_true",
        help="Run until stopped with Ctrl+C.",
    )

    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
        help="Logging level. Default: INFO.",
    )

    arguments = parser.parse_args()

    # Reject a non-positive cycle limit.
    if arguments.cycles is not None and arguments.cycles <= 0:
        parser.error("--cycles must be greater than zero")

    return arguments


def configure_database(database_path):
    """Configure the database path before database modules are imported."""
    if database_path is None:
        return

    # Create the database folder when needed.
    resolved_path = database_path.resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure the project database path.
    os.environ["ADELAIDE_METRO_DATABASE_PATH"] = str(resolved_path)


def build_static_stop_time_index(stop_times_path):
    """Build the static stop-time lookup used for delay calculation."""
    from backend.parsers.static_gtfs import parse_stop_times
    from backend.services.gtfs_converter import build_stop_time_index

    # Check the static GTFS file first.
    if not stop_times_path.is_file():
        raise FileNotFoundError(
            f"Static GTFS stop_times.txt not found: {stop_times_path}"
        )

    # Parse static GTFS stop times.
    stop_times = parse_stop_times(stop_times_path)

    # Build one reusable lookup for all cycles.
    return build_stop_time_index(stop_times)


def main():
    """Start GTFS-Realtime historical collection."""
    arguments = parse_arguments()

    # Configure console logging.
    logging.basicConfig(
        level=getattr(logging, arguments.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Configure the database before importing database modules.
    configure_database(arguments.database)

    from backend.database.connection import DATABASE_PATH
    from backend.database.models import create_tables
    from backend.realtime.collector import GTFSRealtimeCollector
    from backend.services.pipeline import run_collection_and_persist

    # Prepare the static schedule lookup once.
    stop_time_index = build_static_stop_time_index(
        arguments.stop_times.resolve()
    )

    # Ensure database tables and indexes exist.
    create_tables()

    # Create the real Adelaide Metro collector.
    collector = GTFSRealtimeCollector(
        stop_time_index=stop_time_index,
    )

    # Choose bounded or continuous collection.
    max_cycles = None if arguments.continuous else arguments.cycles

    print(f"Database: {DATABASE_PATH}")
    print(f"Static stop-time records: {len(stop_time_index)}")
    print(
        "Polling interval: "
        f"{collector.client.settings.polling_interval_seconds} seconds"
    )

    if max_cycles is None:
        print("Collection mode: continuous (Ctrl+C to stop)")
    else:
        print(f"Collection mode: {max_cycles} cycle(s)")

    try:
        # Collect and persist realtime history.
        results = run_collection_and_persist(
            collector,
            max_cycles=max_cycles,
        )
    except KeyboardInterrupt:
        print("\nCollection stopped by user.")
        return 0

    # Report bounded-run completion.
    print(f"Completed successful cycles: {len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
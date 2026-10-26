"""Export historical GTFS-Realtime records to CSV."""

import argparse
import csv
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Allow imports from the project root.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def configure_database(database_path):
    """Configure the historical database path."""

    # Resolve the selected database.
    resolved_path = database_path.expanduser().resolve()

    # Check that the database exists.
    if not resolved_path.is_file():
        raise FileNotFoundError(
            f"Database file not found: {resolved_path}"
        )

    # Configure the project database connection.
    os.environ["ADELAIDE_METRO_DATABASE_PATH"] = str(
        resolved_path
    )


def export_csv(records, output_path):
    """Write records to a CSV file."""

    # Resolve the output path.
    resolved_output = output_path.expanduser().resolve()

    # Create the parent directory.
    resolved_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Stop when no records match.
    if not records:
        print("No matching records found.")
        return 0

    # Use record keys as CSV columns.
    fieldnames = list(records[0].keys())

    # Write the CSV file.
    with resolved_output.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        # Write the column names.
        writer.writeheader()

        # Write all historical records.
        writer.writerows(records)

    print(f"Exported records: {len(records)}")
    print(f"Output file: {resolved_output}")

    return len(records)


def export_trip_updates(args):
    """Export historical Trip Updates."""

    from backend.database.repository import (
        get_trip_updates_filtered,
    )

    # Query historical Trip Updates.
    records = get_trip_updates_filtered(
        route_id=args.route,
        stop_id=args.stop,
        start_time=args.start_time,
        end_time=args.end_time,
    )

    print("\n=== Trip Update Export ===")
    print(f"Matching records: {len(records)}")

    # Write the result to CSV.
    export_csv(
        records,
        args.output,
    )


def export_vehicle_positions(args):
    """Export historical Vehicle Positions."""

    from backend.database.repository import (
        get_vehicle_positions_filtered,
    )

    # Query historical Vehicle Positions.
    records = get_vehicle_positions_filtered(
        vehicle_id=args.vehicle,
        route_id=args.route,
        start_time=args.start_time,
        end_time=args.end_time,
    )

    print("\n=== Vehicle Position Export ===")
    print(f"Matching records: {len(records)}")

    # Write the result to CSV.
    export_csv(
        records,
        args.output,
    )


def parse_arguments():
    """Read command-line arguments."""

    # Create the main parser.
    parser = argparse.ArgumentParser(
        description=(
            "Query and export historical "
            "GTFS-Realtime data to CSV."
        )
    )

    # Require a historical database.
    parser.add_argument(
        "--database",
        required=True,
        type=Path,
        help="Path to the historical SQLite database.",
    )

    # Create export modes.
    subparsers = parser.add_subparsers(
        dest="export_type",
        required=True,
    )

    # -----------------------------------------
    # Trip Update export arguments
    # -----------------------------------------

    trip_parser = subparsers.add_parser(
        "trip-updates",
        help="Export historical Trip Updates.",
    )

    trip_parser.add_argument(
        "--route",
        help="Filter by route ID.",
    )

    trip_parser.add_argument(
        "--stop",
        help="Filter by stop ID.",
    )

    trip_parser.add_argument(
        "--start-time",
        help="Filter records from this ISO timestamp.",
    )

    trip_parser.add_argument(
        "--end-time",
        help="Filter records up to this ISO timestamp.",
    )

    trip_parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="CSV output path.",
    )

    # -----------------------------------------
    # Vehicle Position export arguments
    # -----------------------------------------

    vehicle_parser = subparsers.add_parser(
        "vehicle-positions",
        help="Export historical Vehicle Positions.",
    )

    vehicle_parser.add_argument(
        "--vehicle",
        help="Filter by vehicle ID.",
    )

    vehicle_parser.add_argument(
        "--route",
        help="Filter by route ID.",
    )

    vehicle_parser.add_argument(
        "--start-time",
        help="Filter records from this ISO timestamp.",
    )

    vehicle_parser.add_argument(
        "--end-time",
        help="Filter records up to this ISO timestamp.",
    )

    vehicle_parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="CSV output path.",
    )

    return parser.parse_args()


def main():
    """Run the historical CSV export."""

    # Read command-line options.
    args = parse_arguments()

    try:
        # Configure the selected database.
        configure_database(args.database)

        # Export the selected record type.
        if args.export_type == "trip-updates":
            export_trip_updates(args)

        elif args.export_type == "vehicle-positions":
            export_vehicle_positions(args)

        return 0

    except (
        FileNotFoundError,
        ValueError,
        OSError,
    ) as error:
        # Display a readable error.
        print(
            f"Export failed: {error}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    # Start the export program.
    raise SystemExit(main())
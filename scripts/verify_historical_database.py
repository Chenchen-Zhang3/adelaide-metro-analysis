"""Verify historical GTFS-Realtime database coverage (v2)."""

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def format_utc(epoch_seconds):
    """Convert Unix seconds to UTC time."""

    # Handle missing timestamps.
    if epoch_seconds is None:
        return "N/A"

    return datetime.fromtimestamp(
        int(epoch_seconds),
        timezone.utc
    ).isoformat()


def julian_to_epoch(julian_day):
    """Convert SQLite Julian dates to Unix seconds."""

    # Handle missing dates.
    if julian_day is None:
        return None

    return round((julian_day - 2440587.5) * 86400)


def show_line(label, value):
    """Print a report item."""

    print(f"  {label}: {value}")


def verify_database(database_path, check_integrity=False):
    """Check historical database coverage."""

    # Resolve the database path.
    path = database_path.expanduser().resolve()

    # Check whether the database exists.
    if not path.is_file():
        raise FileNotFoundError(
            f"Database file not found: {path}"
        )

    # Open the database in read-only mode.
    connection = sqlite3.connect(
        f"{path.as_uri()}?mode=ro",
        uri=True
    )

    try:
        # Prevent database modifications.
        connection.execute("PRAGMA query_only = ON")

        # Start a consistent read transaction.
        connection.execute("BEGIN")

        # Find existing database tables.
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table'"
            )
        }

        # Define required v2 tables.
        required_tables = {
            "schema_metadata",
            "trip_updates",
            "vehicle_positions",
            "collection_cycles",
        }

        # Check for missing tables.
        missing_tables = sorted(
            required_tables - tables
        )

        if missing_tables:
            raise ValueError(
                "Required database tables are missing: "
                + ", ".join(missing_tables)
            )

        # Read the historical storage version.
        version_row = connection.execute(
            """
            SELECT value
            FROM schema_metadata
            WHERE name = 'historical_storage_version'
            """
        ).fetchone()

        version = (
            version_row[0]
            if version_row
            else "unknown"
        )

        # Reject incompatible database versions.
        if version != "2":
            raise ValueError(
                f"Expected database schema v2, found {version}. "
                "Please use a v2 historical database."
            )

        print()
        print("==========================================")
        print(" Sprint 5 Historical Database Verification")
        print("==========================================")

        show_line("Database", path)
        show_line("Schema version", version)

        # -----------------------------------------
        # Trip Update coverage
        # -----------------------------------------

        trip_data = connection.execute(
            """
            SELECT
                COUNT(*),
                COUNT(DISTINCT route_id),
                COUNT(DISTINCT stop_id),
                COUNT(DISTINCT trip_id),
                SUM(
                    CASE
                        WHEN observed_at IS NULL THEN 1
                        ELSE 0
                    END
                ),
                MIN(observed_at),
                MAX(observed_at)
            FROM trip_updates
            """
        ).fetchone()

        print("\n--- Trip Updates ---")

        show_line(
            "Stored observations",
            trip_data[0]
        )

        show_line(
            "Distinct routes",
            trip_data[1]
        )

        show_line(
            "Distinct stops",
            trip_data[2]
        )

        show_line(
            "Distinct trips",
            trip_data[3]
        )

        show_line(
            "Missing observation times",
            trip_data[4] or 0
        )

        show_line(
            "First observation (UTC)",
            format_utc(trip_data[5])
        )

        show_line(
            "Last observation (UTC)",
            format_utc(trip_data[6])
        )

        # -----------------------------------------
        # Vehicle Position coverage
        # -----------------------------------------

        # Use julianday to handle timezone offsets.
        vehicle_data = connection.execute(
            """
            SELECT
                COUNT(*),
                COUNT(DISTINCT route_id),
                COUNT(DISTINCT vehicle_id),
                SUM(
                    CASE
                        WHEN timestamp IS NULL
                             OR timestamp = ''
                        THEN 1
                        ELSE 0
                    END
                ),
                MIN(julianday(timestamp)),
                MAX(julianday(timestamp))
            FROM vehicle_positions
            """
        ).fetchone()

        print("\n--- Vehicle Positions ---")

        show_line(
            "Stored positions",
            vehicle_data[0]
        )

        show_line(
            "Distinct routes",
            vehicle_data[1]
        )

        show_line(
            "Distinct vehicles",
            vehicle_data[2]
        )

        show_line(
            "Missing timestamps",
            vehicle_data[3] or 0
        )

        show_line(
            "First position (UTC)",
            format_utc(
                julian_to_epoch(vehicle_data[4])
            )
        )

        show_line(
            "Last position (UTC)",
            format_utc(
                julian_to_epoch(vehicle_data[5])
            )
        )

        # -----------------------------------------
        # Collection cycle coverage
        # -----------------------------------------

        # Read collection statistics.
        cycle_data = connection.execute(
            """
            SELECT
                COUNT(*),
                MIN(observed_at),
                MAX(observed_at),
                COALESCE(
                    SUM(vehicle_positions_received),
                    0
                ),
                COALESCE(
                    SUM(trip_updates_received),
                    0
                ),
                COALESCE(
                    SUM(trip_updates_stored),
                    0
                ),
                COALESCE(
                    SUM(trip_updates_suppressed),
                    0
                )
            FROM collection_cycles
            """
        ).fetchone()

        # Calculate the largest cycle interval.
        gap_data = connection.execute(
            """
            WITH ordered_cycles AS (
                SELECT
                    observed_at,
                    LAG(observed_at) OVER (
                        ORDER BY observed_at, id
                    ) AS previous_at
                FROM collection_cycles
            )
            SELECT
                MAX(observed_at - previous_at)
            FROM ordered_cycles
            WHERE previous_at IS NOT NULL
            """
        ).fetchone()

        print("\n--- Collection Cycles ---")

        show_line(
            "Successful cycles recorded",
            cycle_data[0]
        )

        show_line(
            "First cycle (UTC)",
            format_utc(cycle_data[1])
        )

        show_line(
            "Last cycle (UTC)",
            format_utc(cycle_data[2])
        )

        show_line(
            "Vehicle positions received",
            cycle_data[3]
        )

        show_line(
            "Trip updates received",
            cycle_data[4]
        )

        show_line(
            "Trip updates stored",
            cycle_data[5]
        )

        show_line(
            "Unchanged updates suppressed",
            cycle_data[6]
        )

        show_line(
            "Largest cycle gap (seconds)",
            gap_data[0]
            if gap_data[0] is not None
            else "N/A"
        )

        # -----------------------------------------
        # Optional database integrity check
        # -----------------------------------------

        if check_integrity:

            # Run a read-only SQLite quick check.
            integrity_result = connection.execute(
                "PRAGMA quick_check(1)"
            ).fetchone()[0]

            print("\n--- Database Integrity ---")

            show_line(
                "Quick check",
                integrity_result
            )

            # Report integrity failures.
            if integrity_result != "ok":
                raise sqlite3.DatabaseError(
                    "Database integrity check failed: "
                    + integrity_result
                )

        # -----------------------------------------
        # Final coverage notes
        # -----------------------------------------

        print("\n--- Verification Notes ---")

        print(
            "Coverage represents stored observations, "
            "not every scheduled service."
        )

        print(
            "Collection gaps may indicate interruptions "
            "or missing feed data."
        )

        print(
            "Suppressed unchanged updates are expected "
            "in historical storage v2."
        )

        # Warn when no historical records exist.
        if trip_data[0] == 0 and vehicle_data[0] == 0:
            print(
                "WARNING: No historical records were found."
            )

        print("\nVerification completed.")

        return 0

    finally:

        # Always close the database connection.
        connection.close()


def main():
    """Read command-line arguments."""

    # Create the argument parser.
    parser = argparse.ArgumentParser(
        description=(
            "Verify Adelaide Metro historical "
            "GTFS-Realtime database coverage."
        )
    )

    # Require an existing database path.
    parser.add_argument(
        "--database",
        required=True,
        type=Path,
        help="Path to the historical SQLite database."
    )

    # Allow optional integrity verification.
    parser.add_argument(
        "--integrity",
        action="store_true",
        help="Run SQLite quick_check."
    )

    # Parse the supplied arguments.
    args = parser.parse_args()

    try:

        # Run the historical database verification.
        return verify_database(
            args.database,
            args.integrity
        )

    except (OSError, ValueError, sqlite3.Error) as error:

        # Display a readable error.
        print(
            f"Verification failed: {error}",
            file=sys.stderr
        )

        return 1


if __name__ == "__main__":

    # Start the verification program.
    raise SystemExit(main())
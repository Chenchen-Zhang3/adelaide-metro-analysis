"""Summarise scheduled service frequency and realtime reliability."""

import argparse
import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ADELAIDE_TIMEZONE = ZoneInfo("Australia/Adelaide")


def parse_time(value):
    """Parse an ISO timestamp."""

    # Handle missing values.
    if value is None:
        return None

    return datetime.fromisoformat(value)


def calculate_rate(count, total):
    """Calculate a percentage rate."""

    # Avoid division by zero.
    if total == 0:
        return 0.0

    return round((count / total) * 100, 2)


def parse_gtfs_time(value):
    """Convert a GTFS time to seconds after midnight."""

    # Split the GTFS time.
    hours, minutes, seconds = map(
        int,
        value.split(":"),
    )

    # GTFS may use hours above 24.
    return (
        hours * 3600
        + minutes * 60
        + seconds
    )


def get_active_service_ids(
    static_gtfs_path,
    service_date,
):
    """Find GTFS services active on a date."""

    calendar_path = static_gtfs_path / "calendar.txt"
    calendar_dates_path = (
        static_gtfs_path / "calendar_dates.txt"
    )

    active_services = set()

    # Map Python weekday to GTFS column.
    weekday_name = service_date.strftime(
        "%A"
    ).lower()

    # Read regular calendar services.
    if calendar_path.is_file():
        with calendar_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            date_number = int(
                service_date.strftime("%Y%m%d")
            )

            for row in reader:
                start_date = int(
                    row["start_date"]
                )
                end_date = int(
                    row["end_date"]
                )

                # Check the date range.
                if not (
                    start_date
                    <= date_number
                    <= end_date
                ):
                    continue

                # Check the weekday.
                if row.get(
                    weekday_name,
                    "0",
                ) == "1":
                    active_services.add(
                        row["service_id"]
                    )

    # Apply calendar exceptions.
    if calendar_dates_path.is_file():
        with calendar_dates_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            target_date = service_date.strftime(
                "%Y%m%d"
            )

            for row in reader:
                # Ignore other dates.
                if row["date"] != target_date:
                    continue

                service_id = row["service_id"]
                exception_type = row[
                    "exception_type"
                ]

                # Add an exceptional service.
                if exception_type == "1":
                    active_services.add(
                        service_id
                    )

                # Remove a cancelled service.
                elif exception_type == "2":
                    active_services.discard(
                        service_id
                    )

    return active_services


def get_route_trip_ids(
    static_gtfs_path,
    route_id,
    active_service_ids,
):
    """Find active trips for a route."""

    trips_path = static_gtfs_path / "trips.txt"

    # Check the GTFS file exists.
    if not trips_path.is_file():
        raise FileNotFoundError(
            f"Missing GTFS file: {trips_path}"
        )

    trip_ids = set()

    # Read route trips.
    with trips_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            # Match the requested route.
            if row["route_id"] != route_id:
                continue

            # Match active services.
            if (
                active_service_ids
                and row["service_id"]
                not in active_service_ids
            ):
                continue

            trip_ids.add(
                row["trip_id"]
            )

    return trip_ids


def get_first_trip_departures(
    static_gtfs_path,
    trip_ids,
):
    """Find the first scheduled departure of each trip."""

    stop_times_path = (
        static_gtfs_path / "stop_times.txt"
    )

    # Check the GTFS file exists.
    if not stop_times_path.is_file():
        raise FileNotFoundError(
            f"Missing GTFS file: {stop_times_path}"
        )

    first_departures = {}

    # Read stop times once.
    with stop_times_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            trip_id = row["trip_id"]

            # Ignore unrelated trips.
            if trip_id not in trip_ids:
                continue

            # Use departure or arrival time.
            time_value = (
                row.get("departure_time")
                or row.get("arrival_time")
            )

            if not time_value:
                continue

            stop_sequence = int(
                row["stop_sequence"]
            )

            current = first_departures.get(
                trip_id
            )

            # Keep the earliest stop sequence.
            if (
                current is None
                or stop_sequence < current[0]
            ):
                first_departures[trip_id] = (
                    stop_sequence,
                    parse_gtfs_time(
                        time_value
                    ),
                )

    return {
        trip_id: value[1]
        for trip_id, value
        in first_departures.items()
    }


def calculate_scheduled_frequency(
    static_gtfs_path,
    route_id,
    start_time,
    end_time,
):
    """Calculate scheduled departures per hour."""

    # Convert the research window to Adelaide time.
    local_start = start_time.astimezone(
        ADELAIDE_TIMEZONE
    )
    local_end = end_time.astimezone(
        ADELAIDE_TIMEZONE
    )

    # Frequency requires one service date.
    if local_start.date() != local_end.date():
        raise ValueError(
            "Frequency window must stay "
            "within one Adelaide service date."
        )

    # Find active timetable services.
    active_services = get_active_service_ids(
        static_gtfs_path,
        local_start.date(),
    )

    # Find route trips.
    trip_ids = get_route_trip_ids(
        static_gtfs_path,
        route_id,
        active_services,
    )

    # Find one departure per trip.
    departures = get_first_trip_departures(
        static_gtfs_path,
        trip_ids,
    )

    # Convert the window to seconds after midnight.
    start_seconds = (
        local_start.hour * 3600
        + local_start.minute * 60
        + local_start.second
    )

    end_seconds = (
        local_end.hour * 3600
        + local_end.minute * 60
        + local_end.second
    )

    # Count scheduled departures in the window.
    scheduled_departures = sum(
        1
        for departure_seconds
        in departures.values()
        if (
            start_seconds
            <= departure_seconds
            < end_seconds
        )
    )

    # Calculate window length.
    hours = (
        end_time - start_time
    ).total_seconds() / 3600

    if hours <= 0:
        raise ValueError(
            "The analysis window must "
            "be greater than zero."
        )

    frequency = round(
        scheduled_departures / hours,
        2,
    )

    return scheduled_departures, frequency


def load_trip_updates(
    connection,
    route_id,
    start_time,
    end_time,
):
    """Load historical Trip Updates."""

    # Convert timestamps to Unix seconds.
    start_epoch = int(
        start_time.timestamp()
    )
    end_epoch = int(
        end_time.timestamp()
    )

    # Query the selected research window.
    rows = connection.execute(
        """
        SELECT
            trip_id,
            route_id,
            stop_id,
            scheduled_arrival,
            delay_seconds,
            observed_at
        FROM trip_updates
        WHERE route_id = ?
          AND observed_at >= ?
          AND observed_at < ?
        ORDER BY observed_at
        """,
        (
            route_id,
            start_epoch,
            end_epoch,
        ),
    ).fetchall()

    return rows


def calculate_reliability(records):
    """Calculate realtime reliability metrics."""

    # Keep records with delay values.
    delays = [
        row["delay_seconds"]
        for row in records
        if row["delay_seconds"] is not None
    ]

    # Count reliability categories.
    early_count = 0
    on_time_count = 0
    delayed_count = 0
    severe_count = 0

    for delay in delays:
        # Negative delay means early.
        if delay < 0:
            early_count += 1

        # Zero to five minutes is on time.
        elif delay <= 300:
            on_time_count += 1

        # Five to ten minutes is delayed.
        elif delay <= 600:
            delayed_count += 1

        # More than ten minutes is severe.
        else:
            severe_count += 1

    # Calculate average delay.
    average_delay = (
        round(
            sum(delays) / len(delays),
            2,
        )
        if delays
        else 0.0
    )

    return {
        "service_observations": len(records),
        "unique_observed_trips": len(
            {
                row["trip_id"]
                for row in records
                if row["trip_id"] is not None
            }
        ),
        "average_delay_seconds": average_delay,
        "on_time_rate_percent": calculate_rate(
            on_time_count,
            len(delays),
        ),
        "delayed_rate_percent": calculate_rate(
            delayed_count,
            len(delays),
        ),
        "severe_delay_rate_percent": calculate_rate(
            severe_count,
            len(delays),
        ),
        "early_rate_percent": calculate_rate(
            early_count,
            len(delays),
        ),
    }


def export_summary(
    summary,
    output_path,
):
    """Write the summary to CSV."""

    # Resolve the output path.
    path = output_path.expanduser().resolve()

    # Create the output folder.
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Write one summary row.
    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(
                summary.keys()
            ),
        )

        writer.writeheader()
        writer.writerow(summary)

    print()
    print(f"CSV exported to: {path}")


def main():
    """Run the service reliability summary."""

    # Create the argument parser.
    parser = argparse.ArgumentParser(
        description=(
            "Summarise scheduled frequency "
            "and historical reliability."
        )
    )

    # Require the historical database.
    parser.add_argument(
        "--database",
        required=True,
        type=Path,
        help="Path to the historical SQLite database.",
    )

    # Require static GTFS data.
    parser.add_argument(
        "--static-gtfs",
        required=True,
        type=Path,
        help="Path to the static GTFS folder.",
    )

    # Require a route.
    parser.add_argument(
        "--route",
        required=True,
        help="Route ID to analyse.",
    )

    # Require a research window.
    parser.add_argument(
        "--start-time",
        required=True,
        help="Start ISO timestamp.",
    )

    parser.add_argument(
        "--end-time",
        required=True,
        help="End ISO timestamp.",
    )

    # Allow CSV export.
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional CSV output path.",
    )

    # Parse the arguments.
    args = parser.parse_args()

    try:
        # Resolve local paths.
        database_path = (
            args.database.expanduser().resolve()
        )

        static_gtfs_path = (
            args.static_gtfs.expanduser().resolve()
        )

        # Validate required paths.
        if not database_path.is_file():
            raise FileNotFoundError(
                f"Database not found: "
                f"{database_path}"
            )

        if not static_gtfs_path.is_dir():
            raise FileNotFoundError(
                f"Static GTFS folder not found: "
                f"{static_gtfs_path}"
            )

        # Parse the research window.
        start_time = parse_time(
            args.start_time
        )

        end_time = parse_time(
            args.end_time
        )

        # Require timezone-aware timestamps.
        if (
            start_time.tzinfo is None
            or end_time.tzinfo is None
        ):
            raise ValueError(
                "start-time and end-time "
                "must include a UTC offset."
            )

        # Validate the time range.
        if start_time >= end_time:
            raise ValueError(
                "start-time must be before end-time."
            )

        # Open the historical database.
        connection = sqlite3.connect(
            database_path
        )

        connection.row_factory = sqlite3.Row

        try:
            # Load realtime reliability records.
            records = load_trip_updates(
                connection,
                args.route,
                start_time,
                end_time,
            )

        finally:
            # Close the database.
            connection.close()

        # Calculate realtime reliability.
        reliability = calculate_reliability(
            records
        )

        # Calculate scheduled frequency.
        (
            scheduled_departures,
            frequency,
        ) = calculate_scheduled_frequency(
            static_gtfs_path,
            args.route,
            start_time,
            end_time,
        )

        # Build the research summary.
        summary = {
            "route_id": args.route,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "scheduled_departures": (
                scheduled_departures
            ),
            "scheduled_frequency_trips_per_hour": (
                frequency
            ),
            **reliability,
        }

        print()
        print(
            "=========================================="
        )
        print(
            " Sprint 5 Service Frequency "
            "and Reliability"
        )
        print(
            "=========================================="
        )

        print(f"\nRoute: {args.route}")
        print(
            "Analysis window:",
            f"{start_time.isoformat()} "
            f"to {end_time.isoformat()}",
        )
        print(
            "Scheduled departures:",
            scheduled_departures,
        )
        print(
            "Scheduled frequency (trips/hour):",
            frequency,
        )
        print(
            "Realtime observations:",
            reliability[
                "service_observations"
            ],
        )
        print(
            "Unique observed trips:",
            reliability[
                "unique_observed_trips"
            ],
        )
        print(
            "Average delay (seconds):",
            reliability[
                "average_delay_seconds"
            ],
        )
        print(
            "On-time rate:",
            f"{reliability['on_time_rate_percent']}%",
        )
        print(
            "Delayed rate:",
            f"{reliability['delayed_rate_percent']}%",
        )
        print(
            "Severe delay rate:",
            f"{reliability['severe_delay_rate_percent']}%",
        )
        print(
            "Early rate:",
            f"{reliability['early_rate_percent']}%",
        )

        # Export when requested.
        if args.output is not None:
            export_summary(
                summary,
                args.output,
            )

        return 0

    except (
        ValueError,
        FileNotFoundError,
        sqlite3.Error,
        OSError,
    ) as error:
        # Display a readable error.
        print(
            f"Summary failed: {error}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    # Start the program.
    raise SystemExit(main())
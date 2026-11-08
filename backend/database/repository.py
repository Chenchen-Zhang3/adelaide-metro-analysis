import logging
import sqlite3
from datetime import datetime
from time import time

from backend.database.connection import get_connection
from backend.database.historical_storage import (
    ADELAIDE_TIMEZONE,
    configured_trip_update_checkpoint_seconds,
    derived_actual_arrival,
    epoch_to_adelaide_iso,
    iso_timestamp_to_epoch,
    validate_derivable_actual_arrival,
)


logger = logging.getLogger(__name__)


OBSERVATION_INITIAL = 0
OBSERVATION_CHANGE = 1
OBSERVATION_CHECKPOINT = 2
OBSERVATION_REAPPEARANCE = 3
OBSERVATION_KIND_NAMES = {
    OBSERVATION_INITIAL: "initial",
    OBSERVATION_CHANGE: "change",
    OBSERVATION_CHECKPOINT: "checkpoint",
    OBSERVATION_REAPPEARANCE: "reappearance",
}


def _rollback_realtime_transaction(connection):
    """Roll back without obscuring the original SQLite persistence error."""
    try:
        connection.rollback()
    except sqlite3.Error:
        logger.exception("Failed to roll back realtime persistence transaction")


def _latest_timestamp(*values):
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _normalise_trip_update(trip_update):
    scheduled_arrival = iso_timestamp_to_epoch(
        trip_update.get("scheduled_arrival"),
        field_name="scheduled_arrival",
        required=True,
    )
    delay_seconds = int(trip_update["delay_seconds"])
    validate_derivable_actual_arrival(
        scheduled_arrival,
        trip_update.get("actual_arrival"),
        delay_seconds,
    )
    return {
        "trip_id": str(trip_update["trip_id"]),
        "route_id": str(trip_update["route_id"]),
        "stop_id": str(trip_update["stop_id"]),
        "scheduled_arrival": scheduled_arrival,
        "delay_seconds": delay_seconds,
        "observed_at": iso_timestamp_to_epoch(trip_update.get("timestamp")),
    }


def _persist_trip_update(cursor, trip_update, checkpoint_seconds):
    try:
        record = _normalise_trip_update(trip_update)
    except (TypeError, ValueError) as error:
        raise sqlite3.IntegrityError(str(error)) from error
    # Identify each prediction by trip, route, and stop.
    key = (record["trip_id"], record["route_id"], record["stop_id"])
    # Retrieve the previous state to detect meaningful changes.
    previous = cursor.execute(
        """
        SELECT scheduled_arrival, delay_seconds, last_seen_at, last_stored_at
        FROM trip_update_current_state
        WHERE trip_id = ? AND route_id = ? AND stop_id = ?
        """,
        key,
    ).fetchone()
    # Classify new, changed, and checkpoint observations.
    # Avoid storing repeated unchanged predictions.
    observation_kind = None
    if previous is None:
        observation_kind = OBSERVATION_INITIAL
    elif (
        previous["scheduled_arrival"] != record["scheduled_arrival"]
        or previous["delay_seconds"] != record["delay_seconds"]
    ):
        observation_kind = OBSERVATION_CHANGE
    elif (
        record["observed_at"] is not None
        and previous["last_stored_at"] is None
    ):
        observation_kind = OBSERVATION_REAPPEARANCE
    elif (
        record["observed_at"] is not None
        and previous["last_seen_at"] is not None
        and record["observed_at"] - previous["last_seen_at"] >= checkpoint_seconds
    ):
        observation_kind = OBSERVATION_REAPPEARANCE
    elif (
        record["observed_at"] is not None
        and previous["last_stored_at"] is not None
        and record["observed_at"] - previous["last_stored_at"] >= checkpoint_seconds
    ):
        observation_kind = OBSERVATION_CHECKPOINT

    inserted = 0
    if observation_kind is not None:
        cursor.execute(
            """
            INSERT OR IGNORE INTO trip_updates (
                trip_id,
                route_id,
                stop_id,
                scheduled_arrival,
                delay_seconds,
                observed_at,
                observation_kind
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                *key,
                record["scheduled_arrival"],
                record["delay_seconds"],
                record["observed_at"],
                observation_kind,
            ),
        )
        inserted = cursor.rowcount

    # Track when the prediction was last observed.
    # Keep observation time separate from storage time.
    previous_last_seen = previous["last_seen_at"] if previous else None
    previous_last_stored = previous["last_stored_at"] if previous else None
    last_seen_at = _latest_timestamp(previous_last_seen, record["observed_at"])
    last_stored_at = previous_last_stored
    if inserted:
        last_stored_at = _latest_timestamp(
            previous_last_stored,
            record["observed_at"],
        )

    # Save the latest prediction state for future comparisons.
    # Preserve state across collection cycles and restarts.
    cursor.execute(
        """
        INSERT INTO trip_update_current_state (
            trip_id,
            route_id,
            stop_id,
            scheduled_arrival,
            delay_seconds,
            last_seen_at,
            last_stored_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(trip_id, route_id, stop_id) DO UPDATE SET
            scheduled_arrival = excluded.scheduled_arrival,
            delay_seconds = excluded.delay_seconds,
            last_seen_at = excluded.last_seen_at,
            last_stored_at = excluded.last_stored_at
        """,
        (
            *key,
            record["scheduled_arrival"],
            record["delay_seconds"],
            last_seen_at,
            last_stored_at,
        ),
    )
    return inserted, observation_kind if inserted else None


def _insert_vehicle_position(cursor, vehicle):
    cursor.execute(
        """
        INSERT OR IGNORE INTO vehicle_positions (
            vehicle_id,
            trip_id,
            route_id,
            latitude,
            longitude,
            timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            vehicle["vehicle_id"],
            vehicle.get("trip_id"),
            vehicle.get("route_id"),
            vehicle["latitude"],
            vehicle["longitude"],
            vehicle.get("timestamp"),
        ),
    )
    return cursor.rowcount


def persist_realtime_collection(
    vehicle_positions,
    trip_updates,
    checkpoint_seconds=None,
):
    """Persist one realtime collection cycle in a single SQLite transaction."""
    vehicle_positions = tuple(vehicle_positions)
    trip_updates = tuple(trip_updates)
    if checkpoint_seconds is None:
        checkpoint_seconds = configured_trip_update_checkpoint_seconds()
    if checkpoint_seconds <= 0:
        raise ValueError("checkpoint_seconds must be greater than zero")

    observed_times = [
        iso_timestamp_to_epoch(record.get("timestamp"))
        for record in (*vehicle_positions, *trip_updates)
        if record.get("timestamp") not in (None, "")
    ]
    cycle_observed_at = max(observed_times) if observed_times else int(time())
    connection = None

    try:
        try:
            connection = get_connection()
            cursor = connection.cursor()
            cursor.execute("BEGIN")
        except sqlite3.Error:
            logger.exception("Failed to set up realtime persistence transaction")
            raise

        try:
            vehicle_positions_inserted = sum(
                _insert_vehicle_position(cursor, vehicle)
                for vehicle in vehicle_positions
            )
        except sqlite3.Error:
            _rollback_realtime_transaction(connection)
            logger.exception(
                "Failed while persisting vehicle position records; transaction rolled back"
            )
            raise

        trip_updates_inserted = 0
        observation_counts = {
            OBSERVATION_INITIAL: 0,
            OBSERVATION_CHANGE: 0,
            OBSERVATION_CHECKPOINT: 0,
            OBSERVATION_REAPPEARANCE: 0,
        }
        try:
            for trip_update in trip_updates:
                inserted, observation_kind = _persist_trip_update(
                    cursor,
                    trip_update,
                    checkpoint_seconds,
                )
                trip_updates_inserted += inserted
                if observation_kind is not None:
                    observation_counts[observation_kind] += 1
        except (sqlite3.Error, TypeError, ValueError):
            _rollback_realtime_transaction(connection)
            logger.exception(
                "Failed while persisting trip update records; transaction rolled back"
            )
            raise

        trip_updates_suppressed = len(trip_updates) - trip_updates_inserted
        try:
            cursor.execute(
                """
                INSERT INTO collection_cycles (
                    observed_at,
                    vehicle_positions_received,
                    trip_updates_received,
                    trip_updates_stored,
                    trip_updates_suppressed
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    cycle_observed_at,
                    len(vehicle_positions),
                    len(trip_updates),
                    trip_updates_inserted,
                    trip_updates_suppressed,
                ),
            )
        except sqlite3.Error:
            _rollback_realtime_transaction(connection)
            logger.exception(
                "Failed while recording the collection cycle; transaction rolled back"
            )
            raise

        try:
            connection.commit()
        except sqlite3.Error:
            _rollback_realtime_transaction(connection)
            logger.exception(
                "Failed to commit realtime persistence transaction; transaction rolled back"
            )
            raise

        summary = {
            "vehicle_positions_received": len(vehicle_positions),
            "vehicle_positions_inserted": vehicle_positions_inserted,
            "trip_updates_received": len(trip_updates),
            "trip_updates_inserted": trip_updates_inserted,
            "trip_updates_suppressed": trip_updates_suppressed,
            "trip_updates_initial": observation_counts[OBSERVATION_INITIAL],
            "trip_updates_changed": observation_counts[OBSERVATION_CHANGE],
            "trip_updates_checkpointed": observation_counts[OBSERVATION_CHECKPOINT],
            "trip_updates_reappeared": observation_counts[OBSERVATION_REAPPEARANCE],
        }
        logger.info(
            "Persisted realtime collection cycle: %d/%d vehicle positions; "
            "%d/%d trip updates stored and %d unchanged updates suppressed",
            summary["vehicle_positions_inserted"],
            summary["vehicle_positions_received"],
            summary["trip_updates_inserted"],
            summary["trip_updates_received"],
            summary["trip_updates_suppressed"],
        )
        return summary
    finally:
        if connection is not None:
            connection.close()


def insert_route(route):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO routes (
            route_id,
            route_short_name,
            route_long_name,
            route_type
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            route["route_id"],
            route.get("route_short_name"),
            route.get("route_long_name"),
            route["route_type"],
        ),
    )

    connection.commit()
    connection.close()


def insert_stop(stop):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO stops (
            stop_id,
            stop_name,
            stop_lat,
            stop_lon
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            stop["stop_id"],
            stop["stop_name"],
            stop["stop_lat"],
            stop["stop_lon"],
        ),
    )

    connection.commit()
    connection.close()


def insert_trip(trip):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO trips (
            trip_id,
            route_id,
            service_id,
            trip_headsign,
            direction_id
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            trip["trip_id"],
            trip["route_id"],
            trip["service_id"],
            trip.get("trip_headsign"),
            trip.get("direction_id"),
        ),
    )

    connection.commit()
    connection.close()


def insert_stop_time(stop_time):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO stop_times (
            trip_id,
            arrival_time,
            departure_time,
            stop_id,
            stop_sequence
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            stop_time["trip_id"],
            stop_time["arrival_time"],
            stop_time["departure_time"],
            stop_time["stop_id"],
            stop_time["stop_sequence"],
        ),
    )

    connection.commit()
    connection.close()


def insert_trip_update(trip_update):
    return persist_realtime_collection((), (trip_update,))[
        "trip_updates_inserted"
    ]


def insert_vehicle_position(vehicle):
    connection = get_connection()
    try:
        inserted = _insert_vehicle_position(connection.cursor(), vehicle)
        connection.commit()
        return inserted
    except sqlite3.Error:
        _rollback_realtime_transaction(connection)
        logger.exception("Failed while persisting a vehicle position record")
        raise
    finally:
        connection.close()


def get_stop(stop_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM stops
        WHERE stop_id = ?
        """,
        (stop_id,),
    )

    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None

    return dict(row)


def get_all_stops():
    """Return all stops from the database."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT stop_id, stop_name, stop_lat, stop_lon
        FROM stops
        ORDER BY stop_name
        """
    )

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]

def get_all_routes():
    """Return all routes from the database."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT route_id, route_short_name, route_long_name, route_type
        FROM routes
        ORDER BY route_short_name, route_id
        """
    )

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]


def _trip_update_row(row):
    scheduled_arrival = epoch_to_adelaide_iso(row["scheduled_arrival"])
    return {
        "id": row["id"],
        "trip_id": row["trip_id"],
        "route_id": row["route_id"],
        "stop_id": row["stop_id"],
        "scheduled_arrival": scheduled_arrival,
        "actual_arrival": derived_actual_arrival(
            row["scheduled_arrival"],
            row["delay_seconds"],
        ),
        "delay_seconds": row["delay_seconds"],
        "timestamp": epoch_to_adelaide_iso(row["observed_at"]),
        "observation_kind": OBSERVATION_KIND_NAMES[row["observation_kind"]],
    }


def _trip_update_range(start_time, end_time):
    """Inclusive read bounds; preserve fractional seconds rather than truncate.

    Legacy repository callers may still supply naive Adelaide timestamps.
    HTTP performance handlers require explicit offsets before calling here.
    """
    def epoch_bound(value):
        if value in (None, ""):
            return None
        parsed = datetime.fromisoformat(str(value))
        if parsed.utcoffset() is None:
            parsed = parsed.replace(tzinfo=ADELAIDE_TIMEZONE)
        return parsed.timestamp()

    start_epoch = epoch_bound(start_time)
    end_epoch = epoch_bound(end_time)
    if start_epoch is not None and end_epoch is not None and start_epoch > end_epoch:
        raise ValueError("start_time must be before or equal to end_time")
    return start_epoch, end_epoch


def _query_trip_updates(conditions=(), parameters=()):
    query = """
        SELECT id, trip_id, route_id, stop_id, scheduled_arrival,
               delay_seconds, observed_at, observation_kind
        FROM trip_updates
    """
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY observed_at IS NULL, observed_at"
    connection = get_connection()
    try:
        rows = connection.execute(query, tuple(parameters)).fetchall()
        return [_trip_update_row(row) for row in rows]
    finally:
        connection.close()


def get_trip_updates(route_id):
    return _query_trip_updates(("route_id = ?",), (route_id,))


def get_trip_updates_by_stop(stop_id):
    return _query_trip_updates(("stop_id = ?",), (stop_id,))


def get_trip_updates_by_time_range(start_time, end_time):
    start_epoch, end_epoch = _trip_update_range(start_time, end_time)
    return _query_trip_updates(
        ("observed_at IS NOT NULL", "observed_at >= ?", "observed_at <= ?"),
        (start_epoch, end_epoch),
    )


def get_trip_updates_filtered(
    route_id=None,
    stop_id=None,
    start_time=None,
    end_time=None,
):
    """Query historical trip updates using optional filters."""

    start_epoch, end_epoch = _trip_update_range(start_time, end_time)
    # Build safe SQL conditions using supplied filters.
    conditions = []
    parameters = []

    # Filter records by route when provided.
    if route_id is not None:
        conditions.append("route_id = ?")
        parameters.append(route_id)

    # Filter records by stop when provided.
    if stop_id is not None:
        conditions.append("stop_id = ?")
        parameters.append(stop_id)
    if start_epoch is not None:
        conditions.extend(("observed_at IS NOT NULL", "observed_at >= ?"))
        parameters.append(start_epoch)
    if end_epoch is not None:
        if "observed_at IS NOT NULL" not in conditions:
            conditions.append("observed_at IS NOT NULL")
        conditions.append("observed_at <= ?")
        parameters.append(end_epoch)
    return _query_trip_updates(conditions, parameters)


def get_routes_by_stop(stop_id):
    """Return all distinct routes that serve the selected stop."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT DISTINCT
            routes.route_id,
            routes.route_short_name,
            routes.route_long_name,
            routes.route_type
        FROM routes
        INNER JOIN trips
            ON routes.route_id = trips.route_id
        INNER JOIN stop_times
            ON trips.trip_id = stop_times.trip_id
        WHERE stop_times.stop_id = ?
        ORDER BY
            routes.route_short_name,
            routes.route_long_name
        """,
        (stop_id,),
    )

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]

def get_vehicle_positions_filtered(
    vehicle_id=None,
    route_id=None,
    start_time=None,
    end_time=None,
):
    # Validate the start timestamp.
    start_datetime = None
    if start_time is not None:
        start_datetime = datetime.fromisoformat(start_time)

    # Validate the end timestamp.
    end_datetime = None
    if end_time is not None:
        end_datetime = datetime.fromisoformat(end_time)

    # Check that the time range is valid.
    if (
        start_datetime is not None
        and end_datetime is not None
        and start_datetime > end_datetime
    ):
        raise ValueError("start_time must be before or equal to end_time")

    # Store query conditions.
    conditions = []

    # Store query parameters.
    parameters = []

    # Add the vehicle filter.
    if vehicle_id is not None:
        conditions.append("vehicle_id = ?")
        parameters.append(vehicle_id)

    # Add the route filter.
    if route_id is not None:
        conditions.append("route_id = ?")
        parameters.append(route_id)

    # Add the start time filter.
    if start_time is not None:
        conditions.append("timestamp IS NOT NULL")
        conditions.append("timestamp >= ?")
        parameters.append(start_time)

    # Add the end time filter.
    if end_time is not None:
        if "timestamp IS NOT NULL" not in conditions:
            conditions.append("timestamp IS NOT NULL")

        conditions.append("timestamp <= ?")
        parameters.append(end_time)

    # Start the vehicle position query.
    query = "SELECT * FROM vehicle_positions"

    # Add filters when provided.
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Return records in historical order.
    query += """
        ORDER BY
            CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END,
            timestamp
    """

    # Open the database connection.
    connection = get_connection()
    cursor = connection.cursor()

    # Run the vehicle position query.
    cursor.execute(query, parameters)

    # Get all matching records.
    rows = cursor.fetchall()

    # Close the database connection.
    connection.close()

    # Return records as dictionaries.
    return [dict(row) for row in rows]

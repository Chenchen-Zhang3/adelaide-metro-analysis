from datetime import datetime

from backend.database.connection import get_connection


def insert_route(route):
    # Open the database connection.
    connection = get_connection()
    cursor = connection.cursor()

    # Insert or update a route record.
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

    # Save and close the connection.
    connection.commit()
    connection.close()


def insert_stop(stop):
    # Open the database connection.
    connection = get_connection()
    cursor = connection.cursor()

    # Insert or update a stop record.
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

    # Save and close the connection.
    connection.commit()
    connection.close()


def insert_trip(trip):
    # Open the database connection.
    connection = get_connection()
    cursor = connection.cursor()

    # Insert or update a trip record.
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

    # Save and close the connection.
    connection.commit()
    connection.close()


def insert_stop_time(stop_time):
    # Open the database connection.
    connection = get_connection()
    cursor = connection.cursor()

    # Insert the record and ignore duplicates.
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

    # Save and close the connection.
    connection.commit()
    connection.close()


def insert_trip_update(trip_update):
    # Open the database connection.
    connection = get_connection()
    cursor = connection.cursor()

    # Insert the record with an optional timestamp.
    cursor.execute(
        """
        INSERT OR IGNORE INTO trip_updates (
            trip_id,
            route_id,
            stop_id,
            scheduled_arrival,
            actual_arrival,
            delay_seconds,
            timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            trip_update["trip_id"],
            trip_update["route_id"],
            trip_update["stop_id"],
            trip_update.get("scheduled_arrival"),
            trip_update.get("actual_arrival"),
            trip_update["delay_seconds"],
            trip_update.get("timestamp"),
        ),
    )

    # Save and close the connection.
    connection.commit()
    connection.close()


def insert_vehicle_position(vehicle):
    # Open the database connection.
    connection = get_connection()
    cursor = connection.cursor()

    # Insert the record with an optional timestamp.
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

    # Save and close the connection.
    connection.commit()
    connection.close()


def get_stop(stop_id):
    # Open the database connection.
    connection = get_connection()
    cursor = connection.cursor()

    # Find a stop by its ID.
    cursor.execute(
        """
        SELECT *
        FROM stops
        WHERE stop_id = ?
        """,
        (stop_id,),
    )

    # Get the matching record.
    row = cursor.fetchone()

    # Close the database connection.
    connection.close()

    # Return None if no record exists.
    if row is None:
        return None

    # Return the record as a dictionary.
    return dict(row)


def get_trip_updates(route_id):
    # Open the database connection.
    connection = get_connection()
    cursor = connection.cursor()

    # Find trip updates for the selected route.
    cursor.execute(
        """
        SELECT *
        FROM trip_updates
        WHERE route_id = ?
        ORDER BY
            CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END,
            timestamp
        """,
        (route_id,),
    )

    # Get all matching records.
    rows = cursor.fetchall()

    # Close the database connection.
    connection.close()

    # Return records as dictionaries.
    return [dict(row) for row in rows]


def get_trip_updates_by_stop(stop_id):
    # Open the database connection.
    connection = get_connection()
    cursor = connection.cursor()

    # Find trip updates for the selected stop.
    cursor.execute(
        """
        SELECT *
        FROM trip_updates
        WHERE stop_id = ?
        ORDER BY
            CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END,
            timestamp
        """,
        (stop_id,),
    )

    # Get all matching records.
    rows = cursor.fetchall()

    # Close the database connection.
    connection.close()

    # Return records as dictionaries.
    return [dict(row) for row in rows]


def get_trip_updates_by_time_range(start_time, end_time):
    # Convert timestamps for validation.
    start_datetime = datetime.fromisoformat(start_time)
    end_datetime = datetime.fromisoformat(end_time)

    # Check that the time range is valid.
    if start_datetime > end_datetime:
        raise ValueError("start_time must be before or equal to end_time")

    # Open the database connection.
    connection = get_connection()
    cursor = connection.cursor()

    # Find records inside the time range.
    cursor.execute(
        """
        SELECT *
        FROM trip_updates
        WHERE timestamp IS NOT NULL
          AND timestamp >= ?
          AND timestamp <= ?
        ORDER BY timestamp
        """,
        (
            start_time,
            end_time,
        ),
    )

    # Get all matching records.
    rows = cursor.fetchall()

    # Close the database connection.
    connection.close()

    # Return records as dictionaries.
    return [dict(row) for row in rows]


def get_trip_updates_filtered(
    route_id=None,
    stop_id=None,
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

    # Store SQL filter conditions.
    conditions = []

    # Store SQL parameter values.
    parameters = []

    # Add the route filter.
    if route_id is not None:
        conditions.append("route_id = ?")
        parameters.append(route_id)

    # Add the stop filter.
    if stop_id is not None:
        conditions.append("stop_id = ?")
        parameters.append(stop_id)

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

    # Start the database query.
    query = "SELECT * FROM trip_updates"

    # Add filters when they are provided.
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Sort timestamped records first.
    query += """
        ORDER BY
            CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END,
            timestamp
    """

    # Open the database connection.
    connection = get_connection()
    cursor = connection.cursor()

    # Run the combined query.
    cursor.execute(query, parameters)

    # Get all matching records.
    rows = cursor.fetchall()

    # Close the database connection.
    connection.close()

    # Return records as dictionaries.
    return [dict(row) for row in rows]
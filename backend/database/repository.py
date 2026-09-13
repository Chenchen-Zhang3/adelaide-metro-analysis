from datetime import datetime

from backend.database.connection import get_connection


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
    connection = get_connection()
    cursor = connection.cursor()

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

    connection.commit()
    connection.close()


def insert_vehicle_position(vehicle):
    connection = get_connection()
    cursor = connection.cursor()

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

    connection.commit()
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


def get_trip_updates(route_id):
    connection = get_connection()
    cursor = connection.cursor()

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

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]


def get_trip_updates_by_stop(stop_id):
    connection = get_connection()
    cursor = connection.cursor()

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

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]


def get_trip_updates_by_time_range(start_time, end_time):
    start_datetime = datetime.fromisoformat(start_time)
    end_datetime = datetime.fromisoformat(end_time)

    if start_datetime > end_datetime:
        raise ValueError("start_time must be before or equal to end_time")

    connection = get_connection()
    cursor = connection.cursor()

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

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]


def get_trip_updates_filtered(
    route_id=None,
    stop_id=None,
    start_time=None,
    end_time=None,
):
    start_datetime = None
    if start_time is not None:
        start_datetime = datetime.fromisoformat(start_time)

    end_datetime = None
    if end_time is not None:
        end_datetime = datetime.fromisoformat(end_time)

    if (
        start_datetime is not None
        and end_datetime is not None
        and start_datetime > end_datetime
    ):
        raise ValueError("start_time must be before or equal to end_time")

    conditions = []
    parameters = []

    if route_id is not None:
        conditions.append("route_id = ?")
        parameters.append(route_id)

    if stop_id is not None:
        conditions.append("stop_id = ?")
        parameters.append(stop_id)

    if start_time is not None:
        conditions.append("timestamp IS NOT NULL")
        conditions.append("timestamp >= ?")
        parameters.append(start_time)

    if end_time is not None:
        if "timestamp IS NOT NULL" not in conditions:
            conditions.append("timestamp IS NOT NULL")

        conditions.append("timestamp <= ?")
        parameters.append(end_time)

    query = "SELECT * FROM trip_updates"

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += """
        ORDER BY
            CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END,
            timestamp
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(query, parameters)

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]


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
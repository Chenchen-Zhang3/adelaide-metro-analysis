from backend.database.connection import get_connection


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

    # Save the change and close the connection.
    connection.commit()
    connection.close()


def get_stop(stop_id):
    # Open the database connection.
    connection = get_connection()
    cursor = connection.cursor()

    # Find a stop by its stop ID.
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

    # Return None if the stop does not exist.
    if row is None:
        return None

    # Convert the database row to a dictionary.
    return dict(row)


def insert_trip_update(trip_update):
    # Open the database connection.
    connection = get_connection()
    cursor = connection.cursor()

    # Insert the trip update and ignore duplicates.
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

    # Save the change and close the connection.
    connection.commit()
    connection.close()


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
        ORDER BY timestamp
        """,
        (route_id,),
    )

    # Get all matching records.
    rows = cursor.fetchall()

    # Close the database connection.
    connection.close()

    # Convert database rows to dictionaries.
    return [dict(row) for row in rows]
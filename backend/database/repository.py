from backend.database.connection import get_connection


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

def insert_trip_update(trip_update):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO trip_updates (
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


def get_trip_updates(route_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM trip_updates
        WHERE route_id = ?
        """,
        (route_id,),
    )

    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]
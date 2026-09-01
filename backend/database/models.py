from backend.database.connection import get_connection


def create_tables():
    # Open a connection to the SQLite database.
    connection = get_connection()

    # Create a cursor for executing SQL statements.
    cursor = connection.cursor()

    # Create the routes table.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            route_id TEXT PRIMARY KEY,
            route_short_name TEXT,
            route_long_name TEXT,
            route_type INTEGER NOT NULL
        )
    """)

    # Create the stops table.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stops (
            stop_id TEXT PRIMARY KEY,
            stop_name TEXT NOT NULL,
            stop_lat REAL NOT NULL,
            stop_lon REAL NOT NULL
        )
    """)

    # Create the trips table.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            trip_id TEXT PRIMARY KEY,
            route_id TEXT NOT NULL,
            service_id TEXT NOT NULL,
            trip_headsign TEXT,
            direction_id INTEGER
        )
    """)

    # Create the stop_times table.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stop_times (
            trip_id TEXT NOT NULL,
            arrival_time TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            stop_id TEXT NOT NULL,
            stop_sequence INTEGER NOT NULL
        )
    """)

    # Create the trip_updates table for processed realtime records.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trip_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id TEXT NOT NULL,
            route_id TEXT NOT NULL,
            stop_id TEXT NOT NULL,
            scheduled_arrival TEXT,
            actual_arrival TEXT,
            delay_seconds INTEGER NOT NULL,
            timestamp TEXT
        )
    """)

    # Create a unique index to prevent duplicate trip update records.
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_trip_updates_unique
        ON trip_updates (
            trip_id,
            route_id,
            stop_id,
            IFNULL(scheduled_arrival, ''),
            IFNULL(actual_arrival, ''),
            delay_seconds,
            IFNULL(timestamp, '')
        )
    """)

    # Create the vehicle_positions table.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicle_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id TEXT NOT NULL,
            trip_id TEXT,
            route_id TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            timestamp TEXT
        )
    """)

    # Save all table changes to the database.
    connection.commit()

    # Close the database connection.
    connection.close()


if __name__ == "__main__":
    # Create the database tables when this file is run directly.
    create_tables()

    # Show a simple success message.
    print("Database tables created successfully.")
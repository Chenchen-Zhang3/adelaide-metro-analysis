from backend.database.connection import get_connection


def create_tables():
    # Open the SQLite database connection.
    connection = get_connection()

    # Create a cursor for SQL commands.
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

    # Create the stop times table.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stop_times (
            trip_id TEXT NOT NULL,
            arrival_time TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            stop_id TEXT NOT NULL,
            stop_sequence INTEGER NOT NULL
        )
    """)

    # Prevent duplicate stop time records.
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_stop_times_unique
        ON stop_times (
            trip_id,
            stop_id,
            stop_sequence
        )
    """)

    # Create the trip updates table.
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

    # Prevent duplicate trip update records.
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

    # Create an index for route queries.
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trip_updates_route
        ON trip_updates (route_id)
    """)

    # Create an index for stop queries.
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trip_updates_stop
        ON trip_updates (stop_id)
    """)

    # Create an index for time queries.
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trip_updates_timestamp
        ON trip_updates (timestamp)
    """)

    # Create an index for combined trip update filters.
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trip_updates_filters
        ON trip_updates (
            route_id,
            stop_id,
            timestamp
        )
    """)

    # Create the vehicle positions table.
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

    # Prevent duplicate vehicle position records.
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_vehicle_positions_unique
        ON vehicle_positions (
            vehicle_id,
            IFNULL(trip_id, ''),
            IFNULL(route_id, ''),
            latitude,
            longitude,
            IFNULL(timestamp, '')
        )
    """)

    # Create an index for vehicle queries.
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vehicle_positions_vehicle
        ON vehicle_positions (vehicle_id)
    """)

    # Create an index for vehicle route queries.
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vehicle_positions_route
        ON vehicle_positions (route_id)
    """)

    # Create an index for vehicle time queries.
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vehicle_positions_timestamp
        ON vehicle_positions (timestamp)
    """)

    # Create an index for combined vehicle filters.
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_vehicle_positions_filters
        ON vehicle_positions (
            vehicle_id,
            route_id,
            timestamp
        )
    """)

    # Save all database changes.
    connection.commit()

    # Close the database connection.
    connection.close()


if __name__ == "__main__":
    # Create all database tables and indexes.
    create_tables()

    # Show a success message.
    print("Database tables created successfully.")
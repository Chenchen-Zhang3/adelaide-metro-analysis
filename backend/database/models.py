from backend.database.connection import get_connection


class HistoricalDatabaseUpgradeRequiredError(RuntimeError):
    """Raised before writes when a legacy historical schema is selected."""


def create_tables():
    # Open the SQLite database connection.
    connection = get_connection()

    # Create a cursor for SQL commands.
    cursor = connection.cursor()

    # Never apply the new storage design in-place to a legacy client database.
    existing_trip_updates = cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'trip_updates'"
    ).fetchone()
    if existing_trip_updates is not None:
        columns = {
            row[1] for row in cursor.execute("PRAGMA table_info(trip_updates)")
        }
        if "actual_arrival" in columns and "observed_at" not in columns:
            connection.close()
            raise HistoricalDatabaseUpgradeRequiredError(
                "Legacy historical database detected. Preserve it as read-only "
                "and configure a new database path for optimised collection."
            )

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

    # Store only state changes and periodic checkpoints. Arrival and observation
    # times use UTC epoch seconds; actual arrival remains derivable.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trip_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id TEXT NOT NULL,
            route_id TEXT NOT NULL,
            stop_id TEXT NOT NULL,
            scheduled_arrival INTEGER NOT NULL,
            delay_seconds INTEGER NOT NULL,
            observed_at INTEGER,
            observation_kind INTEGER NOT NULL
        )
    """)

    # Prevent duplicate stored states at one observation time.
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_trip_updates_unique
        ON trip_updates (
            trip_id,
            route_id,
            stop_id,
            scheduled_arrival,
            delay_seconds,
            IFNULL(observed_at, -1)
        )
    """)

    # Create an index for stop queries.
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trip_updates_stop
        ON trip_updates (stop_id)
    """)

    # Create an index for time queries.
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trip_updates_observed
        ON trip_updates (observed_at)
    """)

    # Its route prefix also supports route-only queries, avoiding a redundant
    # single-column route index.
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trip_updates_filters
        ON trip_updates (
            route_id,
            stop_id,
            observed_at
        )
    """)

    # Persist the latest state so restarts use database state rather than an
    # in-memory cache and cannot re-insert every unchanged prediction.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trip_update_current_state (
            trip_id TEXT NOT NULL,
            route_id TEXT NOT NULL,
            stop_id TEXT NOT NULL,
            scheduled_arrival INTEGER NOT NULL,
            delay_seconds INTEGER NOT NULL,
            last_seen_at INTEGER,
            last_stored_at INTEGER,
            PRIMARY KEY (trip_id, route_id, stop_id)
        ) WITHOUT ROWID
    """)

    # One tiny ledger row per successful cycle separates an unchanged feed from
    # collector downtime without retaining every unchanged Trip Update.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS collection_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            observed_at INTEGER NOT NULL,
            vehicle_positions_received INTEGER NOT NULL,
            trip_updates_received INTEGER NOT NULL,
            trip_updates_stored INTEGER NOT NULL,
            trip_updates_suppressed INTEGER NOT NULL
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_collection_cycles_observed
        ON collection_cycles (observed_at)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_metadata (
            name TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    cursor.execute("""
        INSERT INTO schema_metadata (name, value)
        VALUES ('historical_storage_version', '2')
        ON CONFLICT(name) DO UPDATE SET value = excluded.value
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

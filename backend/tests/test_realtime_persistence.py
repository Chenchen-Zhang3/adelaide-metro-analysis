import sqlite3
import tempfile
import unittest
from pathlib import Path

import backend.database.connection as database_connection
from backend.database.models import create_tables
from backend.database.repository import persist_realtime_collection
from backend.services.pipeline import persist_collection_result


class TestRealtimePersistence(unittest.TestCase):

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_database_path = database_connection.DATABASE_PATH
        database_connection.DATABASE_PATH = (
            Path(self.temporary_directory.name) / "test_adelaide_metro.db"
        )
        create_tables()

    def tearDown(self):
        database_connection.DATABASE_PATH = self.original_database_path
        self.temporary_directory.cleanup()

    def vehicle_position(self, vehicle_id="VEHICLE_001"):
        return {
            "vehicle_id": vehicle_id,
            "trip_id": "TRIP_001",
            "route_id": "ROUTE_001",
            "latitude": -34.9296,
            "longitude": 138.5999,
            "timestamp": "2026-09-17T09:06:00+09:30",
        }

    def trip_update(self, trip_id="TRIP_001"):
        return {
            "trip_id": trip_id,
            "route_id": "ROUTE_001",
            "stop_id": "STOP_001",
            "scheduled_arrival": "2026-09-17T09:00:00+09:30",
            "actual_arrival": "2026-09-17T09:06:00+09:30",
            "delay_seconds": 360,
            "timestamp": "2026-09-17T09:06:00+09:30",
        }

    def count_rows(self, table_name):
        connection = database_connection.get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cursor.fetchone()[0]
        finally:
            connection.close()

    def test_collection_result_persists_both_record_types_in_one_summary(self):
        summary = persist_collection_result({
            "vehicle_positions": [self.vehicle_position()],
            "trip_updates": [self.trip_update()],
        })

        self.assertEqual(summary["vehicle_positions_processed"], 1)
        self.assertEqual(summary["trip_updates_processed"], 1)
        self.assertEqual(summary["vehicle_positions_inserted"], 1)
        self.assertEqual(summary["trip_updates_inserted"], 1)
        self.assertEqual(self.count_rows("vehicle_positions"), 1)
        self.assertEqual(self.count_rows("trip_updates"), 1)

    def test_transaction_persists_multiple_records(self):
        summary = persist_realtime_collection(
            [
                self.vehicle_position("VEHICLE_001"),
                self.vehicle_position("VEHICLE_002"),
            ],
            [
                self.trip_update("TRIP_001"),
                self.trip_update("TRIP_002"),
            ],
        )

        self.assertEqual(summary["vehicle_positions_received"], 2)
        self.assertEqual(summary["vehicle_positions_inserted"], 2)
        self.assertEqual(summary["trip_updates_received"], 2)
        self.assertEqual(summary["trip_updates_inserted"], 2)
        self.assertEqual(self.count_rows("vehicle_positions"), 2)
        self.assertEqual(self.count_rows("trip_updates"), 2)

    def test_duplicate_records_remain_ignored(self):
        vehicle = self.vehicle_position()
        trip_update = self.trip_update()
        persist_realtime_collection([vehicle], [trip_update])

        summary = persist_realtime_collection([vehicle], [trip_update])

        self.assertEqual(summary["vehicle_positions_inserted"], 0)
        self.assertEqual(summary["trip_updates_inserted"], 0)
        self.assertEqual(self.count_rows("vehicle_positions"), 1)
        self.assertEqual(self.count_rows("trip_updates"), 1)

    def test_trip_update_database_error_rolls_back_vehicle_positions(self):
        invalid_trip_update = self.trip_update()
        invalid_trip_update["delay_seconds"] = object()

        with self.assertLogs("backend.database.repository", level="ERROR") as logs:
            with self.assertRaises(sqlite3.Error):
                persist_realtime_collection(
                    [self.vehicle_position()],
                    [invalid_trip_update],
                )

        self.assertIn("trip update records", "\n".join(logs.output))
        self.assertEqual(self.count_rows("vehicle_positions"), 0)
        self.assertEqual(self.count_rows("trip_updates"), 0)

    def test_schema_initialisation_preserves_existing_records(self):
        persist_realtime_collection(
            [self.vehicle_position()],
            [self.trip_update()],
        )

        create_tables()

        self.assertEqual(self.count_rows("vehicle_positions"), 1)
        self.assertEqual(self.count_rows("trip_updates"), 1)

    def test_database_path_can_be_configured_without_business_logic_changes(self):
        configured_path = Path(self.temporary_directory.name) / "configured.db"
        environment = {
            database_connection.DATABASE_PATH_ENVIRONMENT_VARIABLE: str(
                configured_path
            ),
        }

        self.assertEqual(
            database_connection.configured_database_path(environment),
            configured_path,
        )
        self.assertEqual(
            database_connection.configured_database_path({}),
            database_connection.DEFAULT_DATABASE_PATH,
        )


if __name__ == "__main__":
    unittest.main()

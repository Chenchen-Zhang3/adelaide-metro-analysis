import tempfile
import unittest
from pathlib import Path

import backend.database.connection as database_connection
from backend.database.models import create_tables
from backend.database.repository import (
    insert_trip_update,
    insert_vehicle_position,
)
from backend.services.historical_records import (
    prepare_trip_update_record,
    prepare_vehicle_position_record,
)


class TestHistoricalRecords(unittest.TestCase):

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

    def test_prepare_vehicle_position_normalises_optional_values(self):
        record = prepare_vehicle_position_record({
            "vehicle_id": "2606",
            "trip_id": "",
            "route_id": None,
            "latitude": "-34.9",
            "longitude": "138.6",
            "timestamp": "",
        })

        self.assertEqual(record["vehicle_id"], "2606")
        self.assertIsNone(record["trip_id"])
        self.assertIsNone(record["route_id"])
        self.assertIsInstance(record["latitude"], float)
        self.assertIsInstance(record["longitude"], float)
        self.assertIsNone(record["timestamp"])

    def test_prepare_trip_update_preserves_database_field_types(self):
        record = prepare_trip_update_record({
            "trip_id": "1090314",
            "route_id": "721",
            "stop_id": "5281",
            "scheduled_arrival": "2026-08-30T00:56:02+09:30",
            "actual_arrival": "2026-08-30T01:03:52+09:30",
            "delay_seconds": "470",
            "timestamp": None,
        })

        self.assertEqual(record["trip_id"], "1090314")
        self.assertEqual(record["route_id"], "721")
        self.assertEqual(record["stop_id"], "5281")
        self.assertIsInstance(record["delay_seconds"], int)
        self.assertIsNone(record["timestamp"])

    def test_database_repository_accepts_prepared_records_directly(self):
        vehicle = prepare_vehicle_position_record({
            "vehicle_id": "2606",
            "trip_id": "1090375",
            "route_id": "N721",
            "latitude": -34.9,
            "longitude": 138.6,
            "timestamp": "2026-08-30T01:03:05+09:30",
        })
        trip_update = prepare_trip_update_record({
            "trip_id": "1090314",
            "route_id": "721",
            "stop_id": "5281",
            "scheduled_arrival": "2026-08-30T00:56:02+09:30",
            "actual_arrival": "2026-08-30T01:03:52+09:30",
            "delay_seconds": 470,
            "timestamp": "2026-08-30T01:03:05+09:30",
        })

        insert_vehicle_position(vehicle)
        insert_trip_update(trip_update)

        connection = database_connection.get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "SELECT vehicle_id, latitude, longitude FROM vehicle_positions"
        )
        stored_vehicle = dict(cursor.fetchone())
        cursor.execute(
            "SELECT trip_id, route_id, stop_id, delay_seconds FROM trip_updates"
        )
        stored_trip_update = dict(cursor.fetchone())
        connection.close()

        self.assertEqual(stored_vehicle["vehicle_id"], "2606")
        self.assertEqual(stored_vehicle["latitude"], -34.9)
        self.assertEqual(stored_vehicle["longitude"], 138.6)
        self.assertEqual(stored_trip_update["trip_id"], "1090314")
        self.assertEqual(stored_trip_update["route_id"], "721")
        self.assertEqual(stored_trip_update["stop_id"], "5281")
        self.assertEqual(stored_trip_update["delay_seconds"], 470)

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.database.models import create_tables
from backend.database.repository import (
    insert_trip_update,
    get_trip_updates,
)
from backend.analysis.metrics import (
    average_delay,
    delayed_service_count,
    delayed_rate,
    on_time_rate,
)
from backend.analysis.punctuality import classify_punctuality


class TestDatabaseAnalysisIntegration(unittest.TestCase):

    # Create an isolated SQLite database for each integration test.
    # Patch the database path to avoid modifying real or demo data.
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self.database_path = (
            Path(self.temp_dir.name)
            / "integration_test.db"
        )

        self.database_patch = patch(
            "backend.database.connection.DATABASE_PATH",
            self.database_path
        )

        self.database_patch.start()


        create_tables()

    # Restore the original database configuration and remove temporary
    # files after each test to prevent interference between test runs.
    def tearDown(self):
        self.database_patch.stop()
        self.temp_dir.cleanup()


    # Verify the complete database-to-analysis workflow:
    # insert controlled trip updates, retrieve them by route,
    # convert delays into minutes and validate the resulting metrics.
    def test_database_records_can_be_used_by_analysis(self):

        first_update = {
            "trip_id": "TRIP_001",
            "route_id": "ROUTE_001",
            "stop_id": "STOP_001",
            "scheduled_arrival": "2026-08-29T09:00:00+09:30",
            "actual_arrival": "2026-08-29T09:06:00+09:30",
            "delay_seconds": 360,
            "timestamp": "2026-08-29T09:06:00+09:30",
        }

        second_update = {
            "trip_id": "TRIP_002",
            "route_id": "ROUTE_001",
            "stop_id": "STOP_002",
            "scheduled_arrival": "2026-08-29T10:00:00+09:30",
            "actual_arrival": "2026-08-29T10:02:00+09:30",
            "delay_seconds": 120,
            "timestamp": "2026-08-29T10:02:00+09:30",
        }

        insert_trip_update(first_update)
        insert_trip_update(second_update)

        records = get_trip_updates("ROUTE_001")

        self.assertEqual(len(records), 2)

        delays_minutes = [
            record["delay_seconds"] / 60
            for record in records
        ]

        self.assertEqual(
            average_delay(delays_minutes),
            4.0
        )

        self.assertEqual(
            delayed_service_count(delays_minutes),
            1
        )

        self.assertEqual(
            delayed_rate(delays_minutes),
            50.0
        )

        self.assertEqual(
            on_time_rate(delays_minutes),
            50.0
        )

        classifications = [
            classify_punctuality(delay)
            for delay in delays_minutes
        ]

        self.assertCountEqual(
            classifications,
            ["Delayed", "On Time"]
        )


if __name__ == "__main__":
    unittest.main()
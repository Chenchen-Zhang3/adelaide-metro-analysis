import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.database import connection
from backend.database.models import create_tables
from backend.realtime.collector import GTFSRealtimeRetryExhaustedError
from backend.realtime.config import (
    POLLING_INTERVAL_ENVIRONMENT_VARIABLE,
    configured_polling_interval_seconds,
)
from backend.services.historical_collection import (
    HistoricalCollectionRunner,
    load_stop_time_index,
)
from backend.services.pipeline import run_collection_and_persist


class FakeSettings:
    def __init__(self, polling_interval_seconds=15):
        self.polling_interval_seconds = polling_interval_seconds


class FakeClient:
    def __init__(self, polling_interval_seconds=15):
        self.settings = FakeSettings(polling_interval_seconds)


class FakeCollector:
    def __init__(self, polling_interval_seconds=15):
        self.client = FakeClient(polling_interval_seconds)


def successful_persistence_result():
    return {
        "collection_result": {
            "vehicle_positions": [],
            "trip_updates": [],
        },
        "persistence_result": {
            "vehicle_positions_received": 0,
            "vehicle_positions_inserted": 0,
            "trip_updates_received": 0,
            "trip_updates_inserted": 0,
        },
    }


class TestHistoricalCollectionRunner(unittest.TestCase):
    def test_load_stop_time_index_reads_static_file_once(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            static_directory = Path(temporary_directory)
            (static_directory / "stop_times.txt").write_text(
                "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
                "trip-1,08:00:00,08:00:00,stop-1,1\n",
                encoding="utf-8",
            )

            index = load_stop_time_index(static_directory)

        self.assertEqual(
            index[("trip-1", "stop-1", 1)]["arrival_time"],
            "08:00:00",
        )

    def test_initialise_builds_static_index_and_pipeline_only_once(self):
        index_loader = MagicMock(return_value={("trip", "stop", 1): {}})
        create_tables_function = MagicMock()
        pipeline = MagicMock()
        pipeline_factory = MagicMock(return_value=pipeline)
        runner = HistoricalCollectionRunner(
            "static-data",
            pipeline_factory=pipeline_factory,
            create_tables_function=create_tables_function,
            index_loader=index_loader,
        )

        first_pipeline = runner.initialise()
        second_pipeline = runner.initialise()

        self.assertIs(first_pipeline, pipeline)
        self.assertIs(second_pipeline, pipeline)
        index_loader.assert_called_once_with(Path("static-data"))
        create_tables_function.assert_called_once_with()
        pipeline_factory.assert_called_once_with(
            stop_time_index={("trip", "stop", 1): {}}
        )

    def test_runner_reuses_existing_persistence_scheduler(self):
        collector = FakeCollector()
        pipeline = MagicMock(collector=collector)
        runner = HistoricalCollectionRunner(
            "static-data",
            pipeline_factory=MagicMock(return_value=pipeline),
            create_tables_function=MagicMock(),
            index_loader=MagicMock(return_value={}),
        )

        with patch(
            "backend.services.historical_collection.run_collection_and_persist",
            return_value=[successful_persistence_result()],
        ) as run_loop:
            result = runner.run(max_cycles=1)

        self.assertEqual(len(result), 1)
        run_loop.assert_called_once_with(
            collector,
            max_cycles=1,
            stop_event=None,
        )

    def test_multiple_successful_cycles_use_configured_wait(self):
        collector = FakeCollector(polling_interval_seconds=12)
        waits = []

        with patch(
            "backend.services.pipeline.collect_and_persist",
            return_value=successful_persistence_result(),
        ) as collect_and_persist:
            results = run_collection_and_persist(
                collector,
                max_cycles=2,
                sleep_function=waits.append,
            )

        self.assertEqual(len(results), 2)
        self.assertEqual(collect_and_persist.call_count, 2)
        self.assertEqual(waits, [12])

    def test_retry_exhaustion_does_not_stop_following_cycle(self):
        collector = FakeCollector(polling_interval_seconds=9)
        waits = []

        with patch(
            "backend.services.pipeline.collect_and_persist",
            side_effect=[
                GTFSRealtimeRetryExhaustedError("temporary feed error"),
                successful_persistence_result(),
            ],
        ) as collect_and_persist:
            results = run_collection_and_persist(
                collector,
                max_cycles=2,
                sleep_function=waits.append,
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(collect_and_persist.call_count, 2)
        self.assertEqual(waits, [9])

    def test_persistence_failure_is_logged_and_following_cycle_runs(self):
        collector = FakeCollector(polling_interval_seconds=8)
        waits = []

        with patch(
            "backend.services.pipeline.collect_and_persist",
            side_effect=[
                sqlite3.OperationalError("database unavailable"),
                successful_persistence_result(),
            ],
        ):
            with self.assertLogs("backend.services.pipeline", level="ERROR") as logs:
                results = run_collection_and_persist(
                    collector,
                    max_cycles=2,
                    sleep_function=waits.append,
                )

        self.assertEqual(len(results), 1)
        self.assertEqual(waits, [8])
        self.assertIn("failed while persisting data", "\n".join(logs.output))

    def test_stop_event_ends_continuous_runner_without_another_cycle(self):
        collector = FakeCollector(polling_interval_seconds=7)

        class StopAfterFirstWait:
            def __init__(self):
                self.waits = []

            def is_set(self):
                return False

            def wait(self, timeout):
                self.waits.append(timeout)
                return True

        stop_event = StopAfterFirstWait()
        with patch(
            "backend.services.pipeline.collect_and_persist",
            return_value=successful_persistence_result(),
        ) as collect_and_persist:
            results = run_collection_and_persist(
                collector,
                stop_event=stop_event,
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(collect_and_persist.call_count, 1)
        self.assertEqual(stop_event.waits, [7])

    def test_schema_initialisation_does_not_wipe_historical_records(self):
        original_database_path = connection.DATABASE_PATH
        with tempfile.TemporaryDirectory() as temporary_directory:
            connection.DATABASE_PATH = Path(temporary_directory) / "history.db"
            try:
                first_runner = self._runner_with_one_cycle(
                    vehicle_id="vehicle-1",
                    trip_id="trip-1",
                )
                second_runner = self._runner_with_one_cycle(
                    vehicle_id="vehicle-2",
                    trip_id="trip-2",
                )

                first_runner.run(max_cycles=1)
                second_runner.run(max_cycles=1)

                database = sqlite3.connect(connection.DATABASE_PATH)
                try:
                    stored_vehicles = database.execute(
                        "SELECT COUNT(*) FROM vehicle_positions"
                    ).fetchone()[0]
                    stored_updates = database.execute(
                        "SELECT COUNT(*) FROM trip_updates"
                    ).fetchone()[0]
                finally:
                    database.close()
            finally:
                connection.DATABASE_PATH = original_database_path

        self.assertEqual(stored_vehicles, 2)
        self.assertEqual(stored_updates, 2)

    def test_database_connection_creates_configured_parent_directory(self):
        original_database_path = connection.DATABASE_PATH
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "history" / "collector.db"
            connection.DATABASE_PATH = database_path
            try:
                database = connection.get_connection()
                database.close()
            finally:
                connection.DATABASE_PATH = original_database_path

            self.assertTrue(database_path.exists())

    def test_polling_interval_can_be_configured_before_startup(self):
        self.assertEqual(
            configured_polling_interval_seconds(
                {POLLING_INTERVAL_ENVIRONMENT_VARIABLE: "30"}
            ),
            30,
        )
        with self.assertRaises(ValueError):
            configured_polling_interval_seconds(
                {POLLING_INTERVAL_ENVIRONMENT_VARIABLE: "not-a-number"}
            )

    def _runner_with_one_cycle(self, vehicle_id, trip_id):
        collection_result = {
            "vehicle_positions": [
                {
                    "vehicle_id": vehicle_id,
                    "trip_id": trip_id,
                    "route_id": "route-1",
                    "latitude": -34.9,
                    "longitude": 138.6,
                    "timestamp": f"2026-09-20T10:00:0{vehicle_id[-1]}+09:30",
                }
            ],
            "trip_updates": [
                {
                    "trip_id": trip_id,
                    "route_id": "route-1",
                    "stop_id": "stop-1",
                    "scheduled_arrival": "2026-09-20T09:55:00+09:30",
                    "actual_arrival": "2026-09-20T10:00:00+09:30",
                    "delay_seconds": 300,
                    "timestamp": f"2026-09-20T10:00:0{vehicle_id[-1]}+09:30",
                }
            ],
        }
        collector = MagicMock(client=FakeClient())
        collector.collect_once.return_value = collection_result
        pipeline = MagicMock(collector=collector)
        return HistoricalCollectionRunner(
            "static-data",
            pipeline_factory=MagicMock(return_value=pipeline),
            create_tables_function=create_tables,
            index_loader=MagicMock(return_value={}),
        )


if __name__ == "__main__":
    unittest.main()

import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from google.transit import gtfs_realtime_pb2

import backend.database.connection as database_connection
from backend.database.models import create_tables
from backend.database.repository import (
    insert_trip_update,
    insert_vehicle_position,
)
from backend.realtime.client import GTFSRealtimeConnectionError
from backend.realtime.config import GTFSRealtimeCollectionSettings
from backend.realtime.pipeline import GTFSRealtimeProcessingPipeline
from backend.services.pipeline import persist_collection_result


class TestGTFSRealtimeProcessingPipeline(unittest.TestCase):
    def create_vehicle_feed_bytes(self, vehicle_ids=("2606",)):
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "1.0"

        for vehicle_id in vehicle_ids:
            entity = feed.entity.add()
            entity.id = f"vehicle-{vehicle_id}"
            entity.vehicle.vehicle.id = vehicle_id
            entity.vehicle.trip.trip_id = "1090375"
            entity.vehicle.trip.route_id = "N721"
            entity.vehicle.position.latitude = -34.9
            entity.vehicle.position.longitude = 138.6
            entity.vehicle.timestamp = 1788017585

        return feed.SerializeToString()

    def create_mixed_vehicle_feed_bytes(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "1.0"

        for vehicle_id in ("2606", "2607"):
            entity = feed.entity.add()
            entity.id = f"vehicle-{vehicle_id}"
            entity.vehicle.vehicle.id = vehicle_id
            entity.vehicle.position.latitude = -34.9
            entity.vehicle.position.longitude = 138.6

        invalid_entity = feed.entity.add()
        invalid_entity.id = "invalid-vehicle"
        invalid_entity.vehicle.position.latitude = -34.8
        invalid_entity.vehicle.position.longitude = 138.5

        return feed.SerializeToString()

    def create_trip_update_feed_bytes(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "1.0"

        entity = feed.entity.add()
        entity.id = "trip-update"
        trip_update = entity.trip_update
        trip_update.trip.trip_id = "1090314"
        trip_update.trip.route_id = "721"
        trip_update.trip.start_date = "20260829"
        trip_update.timestamp = 1788017585

        stop_update = trip_update.stop_time_update.add()
        stop_update.stop_id = "5281"
        stop_update.stop_sequence = 38
        stop_update.arrival.time = 1788017632

        return feed.SerializeToString()

    def create_mixed_trip_update_feed_bytes(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "1.0"

        for trip_id, route_id in (("1090314", "721"), ("1090315", "722")):
            entity = feed.entity.add()
            entity.id = f"trip-update-{trip_id}"
            trip_update = entity.trip_update
            trip_update.trip.trip_id = trip_id
            trip_update.trip.route_id = route_id
            trip_update.trip.start_date = "20260829"
            stop_update = trip_update.stop_time_update.add()
            stop_update.stop_id = "5281"
            stop_update.stop_sequence = 38
            stop_update.arrival.time = 1788017632

        invalid_entity = feed.entity.add()
        invalid_entity.id = "invalid-trip-update"
        invalid_entity.trip_update.trip.trip_id = "missing-route"
        invalid_entity.trip_update.trip.start_date = "20260829"

        return feed.SerializeToString()

    def create_empty_feed_bytes(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "1.0"
        return feed.SerializeToString()

    def make_client(self, retry_delay_seconds=5, max_retry_attempts=2):
        client = MagicMock()
        client.settings = GTFSRealtimeCollectionSettings(
            retry_delay_seconds=retry_delay_seconds,
            max_retry_attempts=max_retry_attempts,
        )
        client.fetch_vehicle_positions.return_value = self.create_vehicle_feed_bytes()
        client.fetch_trip_updates.return_value = self.create_trip_update_feed_bytes()
        return client

    def test_process_once_returns_database_ready_vehicle_and_trip_records(self):
        client = self.make_client()
        pipeline = GTFSRealtimeProcessingPipeline(
            client=client,
            stop_time_index={
                ("1090314", "5281", 38): {"arrival_time": "24:56:02"},
            },
        )

        result = pipeline.process_once()

        self.assertEqual(result["vehicle_positions"][0]["vehicle_id"], "2606")
        self.assertEqual(result["vehicle_positions"][0]["trip_id"], "1090375")
        self.assertEqual(result["vehicle_positions"][0]["route_id"], "N721")
        self.assertIsInstance(result["vehicle_positions"][0]["latitude"], float)

        trip_update = result["trip_updates"][0]
        self.assertEqual(trip_update["trip_id"], "1090314")
        self.assertEqual(trip_update["stop_id"], "5281")
        self.assertEqual(
            trip_update["scheduled_arrival"],
            "2026-08-30T00:56:02+09:30",
        )
        self.assertEqual(
            trip_update["actual_arrival"],
            "2026-08-30T01:03:52+09:30",
        )
        self.assertEqual(trip_update["delay_seconds"], 470)

    def test_process_once_skips_invalid_entities_and_keeps_valid_records(self):
        client = self.make_client()
        client.fetch_vehicle_positions.return_value = self.create_mixed_vehicle_feed_bytes()
        pipeline = GTFSRealtimeProcessingPipeline(client=client)

        result = pipeline.process_once()

        self.assertEqual(
            [record["vehicle_id"] for record in result["vehicle_positions"]],
            ["2606", "2607"],
        )

    def test_process_once_returns_no_records_for_empty_decoded_feeds(self):
        client = self.make_client()
        empty_feed = self.create_empty_feed_bytes()
        client.fetch_vehicle_positions.return_value = empty_feed
        client.fetch_trip_updates.return_value = empty_feed
        pipeline = GTFSRealtimeProcessingPipeline(client=client)

        self.assertEqual(
            pipeline.process_once(),
            {"vehicle_positions": [], "trip_updates": []},
        )

    def test_process_once_preserves_collector_retry_behaviour(self):
        client = self.make_client(retry_delay_seconds=3)
        client.fetch_vehicle_positions.side_effect = [
            GTFSRealtimeConnectionError("Network unavailable"),
            self.create_vehicle_feed_bytes(),
        ]
        sleep_function = MagicMock()
        pipeline = GTFSRealtimeProcessingPipeline(
            client=client,
            sleep_function=sleep_function,
        )

        result = pipeline.process_once()

        self.assertEqual(client.fetch_vehicle_positions.call_count, 2)
        sleep_function.assert_called_once_with(3)
        self.assertEqual(result["vehicle_positions"][0]["vehicle_id"], "2606")

    def test_process_once_succeeds_after_multiple_temporary_failures(self):
        client = self.make_client(retry_delay_seconds=2)
        client.fetch_vehicle_positions.side_effect = [
            GTFSRealtimeConnectionError("First temporary failure"),
            GTFSRealtimeConnectionError("Second temporary failure"),
            self.create_vehicle_feed_bytes(),
        ]
        sleep_function = MagicMock()
        pipeline = GTFSRealtimeProcessingPipeline(
            client=client,
            sleep_function=sleep_function,
        )

        result = pipeline.process_once()

        self.assertEqual(client.fetch_vehicle_positions.call_count, 3)
        self.assertEqual(sleep_function.call_count, 2)
        sleep_function.assert_called_with(2)
        self.assertEqual(result["vehicle_positions"][0]["vehicle_id"], "2606")

    def test_process_once_skips_invalid_trip_update_and_keeps_valid_records(self):
        client = self.make_client()
        client.fetch_trip_updates.return_value = self.create_mixed_trip_update_feed_bytes()
        pipeline = GTFSRealtimeProcessingPipeline(
            client=client,
            stop_time_index={
                ("1090314", "5281", 38): {"arrival_time": "24:56:02"},
                ("1090315", "5281", 38): {"arrival_time": "24:56:02"},
            },
        )

        result = pipeline.process_once()

        self.assertEqual(
            [record["trip_id"] for record in result["trip_updates"]],
            ["1090314", "1090315"],
        )

    def test_process_once_emits_collection_summary_log(self):
        pipeline = GTFSRealtimeProcessingPipeline(
            client=self.make_client(),
            stop_time_index={
                ("1090314", "5281", 38): {"arrival_time": "24:56:02"},
            },
        )

        with self.assertLogs("backend.realtime.collector", level="INFO") as logs:
            pipeline.process_once()

        output = "\n".join(logs.output)
        self.assertIn("Starting GTFS-Realtime collection cycle", output)
        self.assertIn("Processed 1 vehicle position records", output)
        self.assertIn("Completed GTFS-Realtime collection cycle", output)

    def test_pipeline_output_is_accepted_by_database_repository(self):
        temporary_directory = tempfile.TemporaryDirectory()
        original_database_path = database_connection.DATABASE_PATH
        database_connection.DATABASE_PATH = (
            Path(temporary_directory.name) / "test_adelaide_metro.db"
        )

        try:
            create_tables()
            pipeline = GTFSRealtimeProcessingPipeline(
                client=self.make_client(),
                stop_time_index={
                    ("1090314", "5281", 38): {"arrival_time": "24:56:02"},
                },
            )

            result = pipeline.process_once()
            insert_vehicle_position(result["vehicle_positions"][0])
            insert_trip_update(result["trip_updates"][0])

            connection = database_connection.get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute("SELECT vehicle_id FROM vehicle_positions")
                vehicle = dict(cursor.fetchone())
                cursor.execute(
                    "SELECT trip_id, delay_seconds FROM trip_updates"
                )
                trip_update = dict(cursor.fetchone())
            finally:
                connection.close()

            self.assertEqual(vehicle["vehicle_id"], "2606")
            self.assertEqual(trip_update["trip_id"], "1090314")
            self.assertEqual(trip_update["delay_seconds"], 470)
        finally:
            database_connection.DATABASE_PATH = original_database_path
            temporary_directory.cleanup()

    def test_process_once_output_persists_through_service_handover(self):
        """Verify the processor-to-persistence handover with a temporary DB."""
        temporary_directory = tempfile.TemporaryDirectory()
        original_database_path = database_connection.DATABASE_PATH
        database_connection.DATABASE_PATH = (
            Path(temporary_directory.name) / "test_adelaide_metro.db"
        )

        try:
            create_tables()
            processing_pipeline = GTFSRealtimeProcessingPipeline(
                client=self.make_client(),
                stop_time_index={
                    ("1090314", "5281", 38): {"arrival_time": "24:56:02"},
                },
            )

            collection_result = processing_pipeline.process_once()

            self.assertEqual(
                set(collection_result["vehicle_positions"][0]),
                {
                    "vehicle_id",
                    "trip_id",
                    "route_id",
                    "latitude",
                    "longitude",
                    "timestamp",
                },
            )
            self.assertEqual(
                set(collection_result["trip_updates"][0]),
                {
                    "trip_id",
                    "route_id",
                    "stop_id",
                    "scheduled_arrival",
                    "actual_arrival",
                    "delay_seconds",
                    "timestamp",
                },
            )

            persistence_result = persist_collection_result(collection_result)

            self.assertEqual(
                persistence_result["vehicle_positions_processed"],
                1,
            )
            self.assertEqual(
                persistence_result["trip_updates_processed"],
                1,
            )
            self.assertEqual(
                persistence_result["vehicle_positions_inserted"],
                1,
            )
            self.assertEqual(
                persistence_result["trip_updates_inserted"],
                1,
            )

            connection = database_connection.get_connection()
            try:
                cursor = connection.cursor()
                cursor.execute(
                    "SELECT vehicle_id, route_id, timestamp FROM vehicle_positions"
                )
                vehicle = dict(cursor.fetchone())
                cursor.execute(
                    "SELECT trip_id, stop_id, delay_seconds, observed_at "
                    "FROM trip_updates"
                )
                trip_update = dict(cursor.fetchone())
            finally:
                connection.close()

            self.assertEqual(vehicle["vehicle_id"], "2606")
            self.assertEqual(vehicle["route_id"], "N721")
            self.assertEqual(vehicle["timestamp"], "2026-08-30T01:03:05+09:30")
            self.assertEqual(trip_update["trip_id"], "1090314")
            self.assertEqual(trip_update["stop_id"], "5281")
            self.assertEqual(trip_update["delay_seconds"], 470)
            self.assertEqual(
                trip_update["observed_at"],
                1788017585,
            )
        finally:
            database_connection.DATABASE_PATH = original_database_path
            temporary_directory.cleanup()


if __name__ == "__main__":
    unittest.main()

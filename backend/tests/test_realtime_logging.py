import unittest
from unittest.mock import MagicMock

from google.transit import gtfs_realtime_pb2

from backend.realtime.client import GTFSRealtimeConnectionError
from backend.realtime.collector import (
    GTFSRealtimeCollector,
    GTFSRealtimeRetryExhaustedError,
)
from backend.realtime.config import GTFSRealtimeCollectionSettings


class TestGTFSRealtimeLogging(unittest.TestCase):
    def create_vehicle_feed_bytes(self, include_invalid=False):
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "1.0"

        entity = feed.entity.add()
        entity.id = "valid-vehicle"
        entity.vehicle.vehicle.id = "2606"
        entity.vehicle.position.latitude = -34.9
        entity.vehicle.position.longitude = 138.6

        if include_invalid:
            invalid = feed.entity.add()
            invalid.id = "invalid-vehicle"
            invalid.vehicle.position.latitude = -34.8
            invalid.vehicle.position.longitude = 138.5

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

        stop_update = trip_update.stop_time_update.add()
        stop_update.stop_id = "5281"
        stop_update.stop_sequence = 38
        stop_update.arrival.time = 1788017632

        return feed.SerializeToString()

    def make_client(self, max_retry_attempts=2):
        client = MagicMock()
        client.settings = GTFSRealtimeCollectionSettings(
            max_retry_attempts=max_retry_attempts,
        )
        client.fetch_vehicle_positions.return_value = self.create_vehicle_feed_bytes()
        client.fetch_trip_updates.return_value = self.create_trip_update_feed_bytes()
        return client

    def test_collection_cycle_logs_start_processing_and_completion(self):
        collector = GTFSRealtimeCollector(
            client=self.make_client(),
            stop_time_index={
                ("1090314", "5281", 38): {"arrival_time": "24:56:02"},
            },
        )

        with self.assertLogs("backend.realtime.collector", level="INFO") as logs:
            collector.collect_once()

        output = "\n".join(logs.output)
        self.assertIn("Starting GTFS-Realtime collection cycle", output)
        self.assertIn("Processed 1 vehicle position records", output)
        self.assertIn("Processed 1 trip update records", output)
        self.assertIn("Completed GTFS-Realtime collection cycle", output)

    def test_temporary_failure_logs_retry_context(self):
        client = self.make_client()
        client.fetch_vehicle_positions.side_effect = [
            GTFSRealtimeConnectionError("Network unavailable"),
            self.create_vehicle_feed_bytes(),
        ]
        collector = GTFSRealtimeCollector(
            client=client,
            sleep_function=MagicMock(),
        )

        with self.assertLogs("backend.realtime.collector", level="WARNING") as logs:
            collector.collect_once()

        output = "\n".join(logs.output)
        self.assertIn("Temporary failure retrieving vehicle_positions feed", output)
        self.assertIn("retrying attempt 1/2", output)

    def test_exhausted_retries_log_error_context(self):
        client = self.make_client(max_retry_attempts=0)
        client.fetch_vehicle_positions.side_effect = GTFSRealtimeConnectionError(
            "Network unavailable"
        )
        collector = GTFSRealtimeCollector(client=client)

        with self.assertLogs("backend.realtime.collector", level="ERROR") as logs:
            with self.assertRaises(GTFSRealtimeRetryExhaustedError):
                collector.collect_once()

        self.assertIn("Retries exhausted for vehicle_positions feed", "\n".join(logs.output))

    def test_invalid_entities_log_skip_count_without_payload(self):
        client = self.make_client()
        client.fetch_vehicle_positions.return_value = self.create_vehicle_feed_bytes(
            include_invalid=True
        )
        collector = GTFSRealtimeCollector(client=client)

        with self.assertLogs("backend.realtime.collector", level="WARNING") as logs:
            result = collector.collect_once()

        self.assertEqual(len(result["vehicle_positions"]), 1)
        self.assertIn(
            "Skipped 1 invalid vehicle position entities",
            "\n".join(logs.output),
        )


if __name__ == "__main__":
    unittest.main()

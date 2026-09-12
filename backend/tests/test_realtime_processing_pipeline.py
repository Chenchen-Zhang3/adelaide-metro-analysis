import unittest
from unittest.mock import MagicMock

from google.transit import gtfs_realtime_pb2

from backend.realtime.client import GTFSRealtimeConnectionError
from backend.realtime.config import GTFSRealtimeCollectionSettings
from backend.realtime.pipeline import GTFSRealtimeProcessingPipeline


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

    def create_empty_feed_bytes(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "1.0"
        return feed.SerializeToString()

    def make_client(self, retry_delay_seconds=5):
        client = MagicMock()
        client.settings = GTFSRealtimeCollectionSettings(
            retry_delay_seconds=retry_delay_seconds,
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


if __name__ == "__main__":
    unittest.main()

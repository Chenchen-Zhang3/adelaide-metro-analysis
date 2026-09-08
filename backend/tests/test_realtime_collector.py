import unittest
from unittest.mock import MagicMock

from google.transit import gtfs_realtime_pb2

from backend.realtime.collector import GTFSRealtimeCollector
from backend.realtime.collector import GTFSRealtimeRetryExhaustedError
from backend.realtime.client import (
    GTFSRealtimeConnectionError,
    GTFSRealtimeHTTPError,
    GTFSRealtimeTimeoutError,
)
from backend.realtime.config import GTFSRealtimeCollectionSettings


class TestGTFSRealtimeCollector(unittest.TestCase):

    def create_vehicle_feed_bytes(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "1.0"

        entity = feed.entity.add()
        entity.id = "vehicle-test"
        entity.vehicle.vehicle.id = "2606"
        entity.vehicle.trip.trip_id = "1090375"
        entity.vehicle.trip.route_id = "N721"
        entity.vehicle.position.latitude = -34.9
        entity.vehicle.position.longitude = 138.6
        entity.vehicle.timestamp = 1788017585

        return feed.SerializeToString()

    def create_trip_update_feed_bytes(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "1.0"

        entity = feed.entity.add()
        entity.id = "trip-update-test"
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

    def create_mixed_vehicle_feed_bytes(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "1.0"

        valid_before = feed.entity.add()
        valid_before.id = "valid-vehicle-before"
        valid_before.vehicle.vehicle.id = "2606"
        valid_before.vehicle.position.latitude = -34.9
        valid_before.vehicle.position.longitude = 138.6

        invalid = feed.entity.add()
        invalid.id = "invalid-vehicle"
        invalid.vehicle.position.latitude = -34.8
        invalid.vehicle.position.longitude = 138.5

        valid_after = feed.entity.add()
        valid_after.id = "valid-vehicle-after"
        valid_after.vehicle.vehicle.id = "2607"
        valid_after.vehicle.position.latitude = -34.7
        valid_after.vehicle.position.longitude = 138.4

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
            trip_update.timestamp = 1788017585
            stop_update = trip_update.stop_time_update.add()
            stop_update.stop_id = "5281"
            stop_update.stop_sequence = 38
            stop_update.arrival.time = 1788017632

        invalid = feed.entity.add()
        invalid.id = "invalid-trip-update"
        invalid.trip_update.trip.trip_id = "missing-route"
        invalid.trip_update.trip.start_date = "20260829"

        return feed.SerializeToString()

    def make_client(
        self,
        polling_interval_seconds=60,
        max_retry_attempts=2,
        retry_delay_seconds=5,
    ):
        settings = GTFSRealtimeCollectionSettings(
            polling_interval_seconds=polling_interval_seconds,
            max_retry_attempts=max_retry_attempts,
            retry_delay_seconds=retry_delay_seconds,
        )
        client = MagicMock()
        client.settings = settings
        client.fetch_vehicle_positions.return_value = self.create_vehicle_feed_bytes()
        client.fetch_trip_updates.return_value = self.create_trip_update_feed_bytes()
        return client

    def test_collect_once_uses_existing_client_decoder_and_converters(self):
        client = self.make_client()
        stop_time_index = {
            ("1090314", "5281", 38): {
                "arrival_time": "24:56:02",
            }
        }
        collector = GTFSRealtimeCollector(
            client=client,
            stop_time_index=stop_time_index,
        )

        result = collector.collect_once()

        client.fetch_vehicle_positions.assert_called_once_with()
        client.fetch_trip_updates.assert_called_once_with()
        self.assertEqual(result["vehicle_positions"][0]["vehicle_id"], "2606")
        self.assertEqual(result["trip_updates"][0]["delay_seconds"], 470)

    def test_collect_once_skips_invalid_entities_and_keeps_valid_records(self):
        client = self.make_client()
        client.fetch_vehicle_positions.return_value = self.create_mixed_vehicle_feed_bytes()
        client.fetch_trip_updates.return_value = self.create_mixed_trip_update_feed_bytes()
        stop_time_index = {
            ("1090314", "5281", 38): {"arrival_time": "24:56:02"},
            ("1090315", "5281", 38): {"arrival_time": "24:56:02"},
        }
        collector = GTFSRealtimeCollector(
            client=client,
            stop_time_index=stop_time_index,
        )

        result = collector.collect_once()

        self.assertEqual(
            [record["vehicle_id"] for record in result["vehicle_positions"]],
            ["2606", "2607"],
        )
        self.assertEqual(
            [record["trip_id"] for record in result["trip_updates"]],
            ["1090314", "1090315"],
        )

    def test_retries_connection_failure_then_processes_feed(self):
        client = self.make_client(retry_delay_seconds=3)
        client.fetch_vehicle_positions.side_effect = [
            GTFSRealtimeConnectionError("Network unavailable"),
            self.create_vehicle_feed_bytes(),
        ]
        sleep_function = MagicMock()
        collector = GTFSRealtimeCollector(
            client=client,
            sleep_function=sleep_function,
        )

        result = collector.collect_once()

        self.assertEqual(client.fetch_vehicle_positions.call_count, 2)
        sleep_function.assert_called_once_with(3)
        self.assertEqual(result["vehicle_positions"][0]["vehicle_id"], "2606")

    def test_retries_timeout_and_temporary_http_error(self):
        client = self.make_client(retry_delay_seconds=2)
        client.fetch_vehicle_positions.side_effect = [
            GTFSRealtimeTimeoutError("Request timed out"),
            self.create_vehicle_feed_bytes(),
        ]
        client.fetch_trip_updates.side_effect = [
            GTFSRealtimeHTTPError("https://example.com/trips", 503),
            self.create_trip_update_feed_bytes(),
        ]
        sleep_function = MagicMock()
        collector = GTFSRealtimeCollector(
            client=client,
            sleep_function=sleep_function,
        )

        collector.collect_once()

        self.assertEqual(client.fetch_vehicle_positions.call_count, 2)
        self.assertEqual(client.fetch_trip_updates.call_count, 2)
        self.assertEqual(sleep_function.call_count, 2)
        sleep_function.assert_called_with(2)

    def test_does_not_retry_non_recoverable_http_error(self):
        client = self.make_client()
        client.fetch_vehicle_positions.side_effect = GTFSRealtimeHTTPError(
            "https://example.com/vehicles",
            403,
        )
        sleep_function = MagicMock()
        collector = GTFSRealtimeCollector(
            client=client,
            sleep_function=sleep_function,
        )

        with self.assertRaises(GTFSRealtimeHTTPError):
            collector.collect_once()

        client.fetch_vehicle_positions.assert_called_once_with()
        sleep_function.assert_not_called()

    def test_raises_after_configured_retry_attempts_are_exhausted(self):
        client = self.make_client(max_retry_attempts=1, retry_delay_seconds=4)
        client.fetch_vehicle_positions.side_effect = GTFSRealtimeConnectionError(
            "Network unavailable"
        )
        sleep_function = MagicMock()
        collector = GTFSRealtimeCollector(
            client=client,
            sleep_function=sleep_function,
        )

        with self.assertRaises(GTFSRealtimeRetryExhaustedError):
            collector.collect_once()

        self.assertEqual(client.fetch_vehicle_positions.call_count, 2)
        sleep_function.assert_called_once_with(4)

    def test_retries_exhausted_cycle_does_not_stop_future_cycles(self):
        client = self.make_client(max_retry_attempts=1, retry_delay_seconds=4)
        sleep_function = MagicMock()
        collector = GTFSRealtimeCollector(
            client=client,
            sleep_function=sleep_function,
        )
        collector.collect_once = MagicMock(side_effect=[
            GTFSRealtimeRetryExhaustedError("Retry attempts exhausted"),
            {"records": []},
        ])

        result = collector.run(max_cycles=2)

        self.assertEqual(result, [{"records": []}])
        self.assertEqual(collector.collect_once.call_count, 2)
        sleep_function.assert_called_once_with(60)

    def test_run_uses_configured_interval_between_cycles(self):
        client = self.make_client(polling_interval_seconds=25)
        sleep_function = MagicMock()
        collector = GTFSRealtimeCollector(
            client=client,
            sleep_function=sleep_function,
        )
        collector.collect_once = MagicMock(return_value={"records": []})

        result = collector.run(max_cycles=2)

        self.assertEqual(result, [{"records": []}, {"records": []}])
        self.assertEqual(collector.collect_once.call_count, 2)
        sleep_function.assert_called_once_with(25)

    def test_run_does_not_wait_after_final_cycle(self):
        client = self.make_client()
        sleep_function = MagicMock()
        collector = GTFSRealtimeCollector(
            client=client,
            sleep_function=sleep_function,
        )
        collector.collect_once = MagicMock(return_value={"records": []})

        collector.run(max_cycles=1)

        sleep_function.assert_not_called()


if __name__ == "__main__":
    unittest.main()

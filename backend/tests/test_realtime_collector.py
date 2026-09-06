import unittest
from unittest.mock import MagicMock

from google.transit import gtfs_realtime_pb2

from backend.realtime.collector import GTFSRealtimeCollector
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

    def make_client(self, polling_interval_seconds=60):
        settings = GTFSRealtimeCollectionSettings(
            polling_interval_seconds=polling_interval_seconds,
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

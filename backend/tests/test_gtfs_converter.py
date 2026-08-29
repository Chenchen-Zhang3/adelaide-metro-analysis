import unittest

from google.transit import gtfs_realtime_pb2

from backend.services.gtfs_converter import (
    convert_stop,
    convert_route,
    convert_trip,
    convert_stop_time,
    convert_vehicle_position,
    convert_trip_update,
    build_stop_time_index,
    gtfs_time_to_datetime,
)

class TestGTFSConverter(unittest.TestCase):

    def test_convert_stop(self):
        stop = {
            "stop_id": "100799",
            "stop_name": "Test Stop",
            "stop_lat": "-34.9",
            "stop_lon": "138.6",
        }

        result = convert_stop(stop)

        self.assertEqual(result["stop_id"], "100799")
        self.assertEqual(result["stop_name"], "Test Stop")
        self.assertIsInstance(result["stop_lat"], float)
        self.assertIsInstance(result["stop_lon"], float)

    def test_convert_route(self):
        route = {
            "route_id": "721",
            "route_short_name": "721",
            "route_long_name": "Test Route",
            "route_type": "3",
        }

        result = convert_route(route)

        self.assertEqual(result["route_id"], "721")
        self.assertEqual(result["route_type"], 3)

    def test_convert_trip(self):
        trip = {
            "trip_id": "1090375",
            "route_id": "N721",
            "service_id": "100",
            "trip_headsign": "City",
            "direction_id": 1,
        }

        result = convert_trip(trip)

        self.assertEqual(result["trip_id"], "1090375")
        self.assertEqual(result["route_id"], "N721")
        self.assertEqual(result["direction_id"], 1)

    def test_convert_stop_time(self):
        stop_time = {
            "trip_id": "1090375",
            "arrival_time": "24:56:02",
            "departure_time": "24:56:02",
            "stop_id": "5281",
            "stop_sequence": "38",
        }

        result = convert_stop_time(stop_time)

        self.assertEqual(result["stop_sequence"], 38)
        self.assertEqual(result["arrival_time"], "24:56:02")

    def test_gtfs_time_over_24_hours(self):
        result = gtfs_time_to_datetime(
            "20260829",
            "24:56:02"
        )

        self.assertEqual(
            result.isoformat(),
            "2026-08-30T00:56:02+09:30"
        )

    def test_build_stop_time_index(self):
        stop_times = [
            {
                "trip_id": "1090375",
                "stop_id": "5281",
                "stop_sequence": 38,
                "arrival_time": "24:56:02",
            }
        ]

        index = build_stop_time_index(stop_times)

        self.assertIn(
            ("1090375", "5281", 38),
            index
        )

    def test_convert_vehicle_position(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.header.gtfs_realtime_version = "1.0"

        entity = feed.entity.add()
        entity.id = "vehicle-test"

        vehicle = entity.vehicle
        vehicle.vehicle.id = "2606"
        vehicle.trip.trip_id = "1090375"
        vehicle.trip.route_id = "N721"
        vehicle.position.latitude = -34.9
        vehicle.position.longitude = 138.6
        vehicle.timestamp = 1788017585

        result = convert_vehicle_position(entity)

        self.assertEqual(result["vehicle_id"], "2606")
        self.assertEqual(result["trip_id"], "1090375")
        self.assertEqual(result["route_id"], "N721")
        self.assertIsInstance(result["latitude"], float)
        self.assertIsNotNone(result["timestamp"])


    def test_convert_trip_update(self):
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

        stop_time_index = {
            ("1090314", "5281", 38): {
                "trip_id": "1090314",
                "stop_id": "5281",
                "stop_sequence": 38,
                "arrival_time": "24:56:02",
                "departure_time": "24:56:02",
            }
        }

        result = convert_trip_update(
            entity,
            stop_time_index
        )

        self.assertEqual(len(result), 1)

        record = result[0]

        self.assertEqual(record["trip_id"], "1090314")
        self.assertEqual(record["route_id"], "721")
        self.assertEqual(record["stop_id"], "5281")
        self.assertEqual(
            record["scheduled_arrival"],
            "2026-08-30T00:56:02+09:30"
        )
        self.assertEqual(
            record["actual_arrival"],
            "2026-08-30T01:03:52+09:30"
        )
        self.assertEqual(record["delay_seconds"], 470)
        self.assertIsNotNone(record["timestamp"])

        


if __name__ == "__main__":
    unittest.main()
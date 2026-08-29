import csv
import tempfile
import unittest
from pathlib import Path

from backend.parsers.static_gtfs import (
    parse_stops,
    parse_routes,
    parse_trips,
    parse_stop_times,
)

class TestStaticGTFSParser(unittest.TestCase):

    def create_csv_file(self, fieldnames, rows):
        temp_dir = tempfile.TemporaryDirectory()
        file_path = Path(temp_dir.name) / "test.txt"

        with file_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        self.addCleanup(temp_dir.cleanup)
        return file_path

    def test_parse_stops(self):
        file_path = self.create_csv_file(
            ["stop_id", "stop_name", "stop_lat", "stop_lon"],
            [
                {
                    "stop_id": "100799",
                    "stop_name": "Test Stop",
                    "stop_lat": "-34.949104",
                    "stop_lon": "138.634403",
                }
            ],
        )

        stops = parse_stops(file_path)

        self.assertEqual(len(stops), 1)
        self.assertEqual(stops[0]["stop_id"], "100799")
        self.assertIsInstance(stops[0]["stop_lat"], float)
        self.assertIsInstance(stops[0]["stop_lon"], float)

    def test_parse_routes(self):
        file_path = self.create_csv_file(
            [
                "route_id",
                "route_short_name",
                "route_long_name",
                "route_type",
            ],
            [
                {
                    "route_id": "100E",
                    "route_short_name": "100E",
                    "route_long_name": "Test Route",
                    "route_type": "3",
                }
            ],
        )

        routes = parse_routes(file_path)

        self.assertEqual(len(routes), 1)
        self.assertEqual(routes[0]["route_id"], "100E")
        self.assertIsInstance(routes[0]["route_type"], int)

    def test_parse_trips(self):
        file_path = self.create_csv_file(
            [
                "route_id",
                "service_id",
                "trip_id",
                "direction_id",
                "wheelchair_accessible",
            ],
            [
                {
                    "route_id": "BEL",
                    "service_id": "8603",
                    "trip_id": "683794",
                    "direction_id": "0",
                    "wheelchair_accessible": "1",
                }
            ],
        )

        trips = parse_trips(file_path)

        self.assertEqual(len(trips), 1)
        self.assertEqual(trips[0]["trip_id"], "683794")
        self.assertIsInstance(trips[0]["direction_id"], int)
        self.assertIsInstance(trips[0]["wheelchair_accessible"], int)

    def test_missing_required_stop_field(self):
        file_path = self.create_csv_file(
            ["stop_id", "stop_name", "stop_lat"],
            [
                {
                    "stop_id": "100799",
                    "stop_name": "Test Stop",
                    "stop_lat": "-34.949104",
                }
            ],
        )

        with self.assertRaises(ValueError):
            parse_stops(file_path)

    def test_parse_stop_times(self):
        file_path = self.create_csv_file(
            [
                "trip_id",
                "arrival_time",
                "departure_time",
                "stop_id",
                "stop_sequence",
            ],
            [
                {
                "trip_id": "TRIP_001",
                "arrival_time": "24:56:02",
                "departure_time": "24:56:02",
                "stop_id": "STOP_001",
                "stop_sequence": "38",
                }
            ],
        )

        stop_times = parse_stop_times(file_path)

        self.assertEqual(len(stop_times), 1)
        self.assertEqual(stop_times[0]["trip_id"], "TRIP_001")
        self.assertEqual(stop_times[0]["stop_id"], "STOP_001")
        self.assertEqual(stop_times[0]["arrival_time"], "24:56:02")
        self.assertEqual(stop_times[0]["stop_sequence"], 38)
        self.assertIsInstance(stop_times[0]["stop_sequence"], int)


if __name__ == "__main__":
    unittest.main()
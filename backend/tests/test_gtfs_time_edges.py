import unittest
from datetime import datetime, timedelta, timezone

from google.transit import gtfs_realtime_pb2

from backend.services.gtfs_converter import (
    ADELAIDE_TIMEZONE,
    calculate_delay_seconds,
    convert_trip_update,
    gtfs_time_to_datetime,
    unix_timestamp_to_datetime,
    unix_timestamp_to_iso,
)


class TestGTFSTimeEdges(unittest.TestCase):

    def test_gtfs_time_beyond_24_hours_rolls_into_next_day(self):
        result = gtfs_time_to_datetime("20260908", "25:15:30")

        self.assertEqual(
            result.isoformat(),
            "2026-09-09T01:15:30+09:30",
        )

    def test_normal_gtfs_time_remains_on_service_date(self):
        result = gtfs_time_to_datetime("20260908", "10:15:00")

        self.assertEqual(
            result.isoformat(),
            "2026-09-08T10:15:00+09:30",
        )

    def test_gtfs_time_rejects_invalid_clock_values(self):
        with self.assertRaises(ValueError):
            gtfs_time_to_datetime("20260908", "10:60:00")

    def test_raw_delay_preserves_early_zero_and_late_values(self):
        scheduled = gtfs_time_to_datetime("20260908", "10:00:00")

        self.assertEqual(
            calculate_delay_seconds(scheduled, scheduled - timedelta(minutes=2)),
            -120,
        )
        self.assertEqual(calculate_delay_seconds(scheduled, scheduled), 0)
        self.assertEqual(
            calculate_delay_seconds(scheduled, scheduled + timedelta(minutes=5)),
            300,
        )

    def test_midnight_boundary_trip_update_calculates_correct_delay(self):
        scheduled = gtfs_time_to_datetime("20260908", "24:30:00")
        actual = scheduled + timedelta(minutes=5)
        feed = gtfs_realtime_pb2.FeedMessage()
        entity = feed.entity.add()
        entity.id = "midnight-trip-update"
        trip_update = entity.trip_update
        trip_update.trip.trip_id = "1090314"
        trip_update.trip.route_id = "721"
        trip_update.trip.start_date = "20260908"
        stop_update = trip_update.stop_time_update.add()
        stop_update.stop_id = "5281"
        stop_update.stop_sequence = 38
        stop_update.arrival.time = int(actual.timestamp())

        records = convert_trip_update(entity, {
            ("1090314", "5281", 38): {"arrival_time": "24:30:00"},
        })

        self.assertEqual(records[0]["scheduled_arrival"], scheduled.isoformat())
        self.assertEqual(records[0]["delay_seconds"], 300)

    def test_missing_arrival_or_scheduled_match_does_not_create_delay(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        entity = feed.entity.add()
        entity.id = "incomplete-trip-update"
        trip_update = entity.trip_update
        trip_update.trip.trip_id = "1090314"
        trip_update.trip.route_id = "721"
        trip_update.trip.start_date = "20260908"

        missing_arrival = trip_update.stop_time_update.add()
        missing_arrival.stop_id = "5281"
        missing_arrival.stop_sequence = 38

        unmatched_stop = trip_update.stop_time_update.add()
        unmatched_stop.stop_id = "9999"
        unmatched_stop.stop_sequence = 39
        unmatched_stop.arrival.time = 1788780600

        records = convert_trip_update(entity, {
            ("1090314", "5281", 38): {"arrival_time": "10:00:00"},
        })

        self.assertEqual(records, [])

    def test_unix_timestamp_zero_is_not_treated_as_missing(self):
        result = unix_timestamp_to_iso(0)

        self.assertEqual(result, "1970-01-01T09:30:00+09:30")
        self.assertIsNone(unix_timestamp_to_iso(None))

    def test_adelaide_timezone_uses_daylight_saving_offset(self):
        timestamp = datetime(2026, 1, 15, tzinfo=timezone.utc).timestamp()
        result = unix_timestamp_to_datetime(timestamp)

        self.assertEqual(result.tzinfo, ADELAIDE_TIMEZONE)
        self.assertEqual(result.utcoffset(), timedelta(hours=10, minutes=30))

import unittest

from google.transit import gtfs_realtime_pb2

from backend.realtime.validation import (
    is_valid_stop_time_update,
    is_valid_trip_update,
    is_valid_vehicle_position,
)


class TestGTFSRealtimeValidation(unittest.TestCase):

    def test_vehicle_requires_vehicle_id_and_position(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        entity = feed.entity.add()
        entity.vehicle.vehicle.id = "2606"
        entity.vehicle.position.latitude = -34.9
        entity.vehicle.position.longitude = 138.6

        self.assertTrue(is_valid_vehicle_position(entity))

        missing_vehicle_id = feed.entity.add()
        missing_vehicle_id.vehicle.position.latitude = -34.9
        self.assertFalse(is_valid_vehicle_position(missing_vehicle_id))

        missing_position = feed.entity.add()
        missing_position.vehicle.vehicle.id = "2607"
        self.assertFalse(is_valid_vehicle_position(missing_position))

    def test_vehicle_timestamp_is_optional(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        entity = feed.entity.add()
        entity.vehicle.vehicle.id = "2606"
        entity.vehicle.position.latitude = -34.9
        entity.vehicle.position.longitude = 138.6

        self.assertTrue(is_valid_vehicle_position(entity))

    def test_trip_update_requires_processing_identifiers(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        entity = feed.entity.add()
        trip = entity.trip_update.trip
        trip.trip_id = "1090314"
        trip.route_id = "721"
        trip.start_date = "20260829"

        self.assertTrue(is_valid_trip_update(entity))

        missing_route = feed.entity.add()
        missing_route.trip_update.trip.trip_id = "1090315"
        missing_route.trip_update.trip.start_date = "20260829"
        self.assertFalse(is_valid_trip_update(missing_route))

    def test_stop_update_requires_matching_and_arrival_fields(self):
        feed = gtfs_realtime_pb2.FeedMessage()
        valid_stop = feed.entity.add().trip_update.stop_time_update.add()
        valid_stop.stop_id = "5281"
        valid_stop.stop_sequence = 38
        valid_stop.arrival.time = 1788017632

        self.assertTrue(is_valid_stop_time_update(valid_stop))

        missing_stop_id = feed.entity.add().trip_update.stop_time_update.add()
        missing_stop_id.stop_sequence = 38
        missing_stop_id.arrival.time = 1788017632
        self.assertFalse(is_valid_stop_time_update(missing_stop_id))

        missing_arrival = feed.entity.add().trip_update.stop_time_update.add()
        missing_arrival.stop_id = "5281"
        missing_arrival.stop_sequence = 38
        self.assertFalse(is_valid_stop_time_update(missing_arrival))

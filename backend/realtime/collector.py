"""Scheduled collection for the existing GTFS-Realtime processing pipeline."""

from time import sleep

from backend.realtime.client import GTFSRealtimeClient
from backend.realtime.decoder import decode_feed
from backend.services.gtfs_converter import (
    convert_trip_update,
    convert_vehicle_position,
)


class GTFSRealtimeCollector:
    """Periodically fetch and process the supported GTFS-Realtime feeds.

    The collector coordinates existing components only: the HTTP client obtains
    bytes, the decoder creates a FeedMessage, and the converter creates the
    project's shared records. Retry and record-validation policy intentionally
    belong to later Sprint 2 tasks.
    """

    def __init__(
        self,
        client=None,
        stop_time_index=None,
        sleep_function=sleep,
    ):
        self.client = client or GTFSRealtimeClient()
        self.stop_time_index = stop_time_index or {}
        self.sleep_function = sleep_function

    def collect_once(self):
        """Fetch, decode and convert one Vehicle Positions and Trip Updates cycle."""
        vehicle_feed = decode_feed(self.client.fetch_vehicle_positions())
        trip_update_feed = decode_feed(self.client.fetch_trip_updates())

        vehicle_positions = [
            convert_vehicle_position(entity)
            for entity in vehicle_feed.entity
            if entity.HasField("vehicle")
        ]
        trip_updates = [
            record
            for entity in trip_update_feed.entity
            if entity.HasField("trip_update")
            for record in convert_trip_update(entity, self.stop_time_index)
        ]

        return {
            "vehicle_positions": vehicle_positions,
            "trip_updates": trip_updates,
        }

    def run(self, max_cycles=None):
        """Run collection cycles, waiting for the configured polling interval.

        ``max_cycles`` is optional for the long-running service and lets tests
        or command-line callers complete a known number of cycles.
        """
        completed_cycles = 0
        results = []

        while max_cycles is None or completed_cycles < max_cycles:
            results.append(self.collect_once())
            completed_cycles += 1

            if max_cycles is None or completed_cycles < max_cycles:
                self.sleep_function(
                    self.client.settings.polling_interval_seconds
                )

        return results

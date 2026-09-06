"""Configuration for collecting Adelaide Metro GTFS-Realtime feeds.

This module contains settings only.  Scheduling a collection cycle is handled
separately so that the polling policy can be adjusted without changing client
or processing code.
"""

from dataclasses import dataclass


BASE_URL = "https://gtfs.adelaidemetro.com.au/v1"


@dataclass(frozen=True)
class GTFSRealtimeCollectionSettings:
    """Reusable parameters used by GTFS-Realtime collection."""

    vehicle_positions_url: str = f"{BASE_URL}/realtime/vehicle_positions"
    trip_updates_url: str = f"{BASE_URL}/realtime/trip_updates"
    service_alerts_url: str = f"{BASE_URL}/realtime/service_alerts"
    polling_interval_seconds: int = 60
    request_timeout_seconds: int = 10
    max_retry_attempts: int = 2
    retry_delay_seconds: int = 5
    user_agent: str = "adelaide-metro-analysis/1.0"

    def __post_init__(self):
        if self.polling_interval_seconds <= 0:
            raise ValueError("Polling interval must be greater than zero")
        if self.request_timeout_seconds <= 0:
            raise ValueError("Request timeout must be greater than zero")
        if self.max_retry_attempts < 0:
            raise ValueError("Maximum retry attempts cannot be negative")
        if self.retry_delay_seconds <= 0:
            raise ValueError("Retry delay must be greater than zero")


DEFAULT_COLLECTION_SETTINGS = GTFSRealtimeCollectionSettings()

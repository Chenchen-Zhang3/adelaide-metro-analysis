from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import logging

from backend.realtime.config import DEFAULT_COLLECTION_SETTINGS


logger = logging.getLogger(__name__)


class GTFSRealtimeRequestError(RuntimeError):
    """Base error for a GTFS-Realtime HTTP request."""


class GTFSRealtimeHTTPError(GTFSRealtimeRequestError):
    """HTTP error that preserves its status code for retry decisions."""

    def __init__(self, url, status_code):
        super().__init__(
            f"GTFS-Realtime request failed with HTTP {status_code}: {url}"
        )
        self.status_code = status_code


class GTFSRealtimeConnectionError(GTFSRealtimeRequestError):
    """Connection failure while contacting a GTFS-Realtime endpoint."""


class GTFSRealtimeTimeoutError(GTFSRealtimeRequestError):
    """Timeout while contacting a GTFS-Realtime endpoint."""


class GTFSRealtimeClient:
    def __init__(self, settings=DEFAULT_COLLECTION_SETTINGS):
        self.settings = settings

    def fetch(self, url):
        logger.debug("Requesting GTFS-Realtime feed: %s", url)
        request = Request(
            url,
            headers={
                "User-Agent": self.settings.user_agent
            },
        )

        try:
            with urlopen(
                request,
                timeout=self.settings.request_timeout_seconds,
            ) as response:
                data = response.read()

        except HTTPError as error:
            raise GTFSRealtimeHTTPError(
                url,
                error.code,
            ) from error

        except URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise GTFSRealtimeTimeoutError(
                    f"GTFS-Realtime request timed out: {url}"
                ) from error

            raise GTFSRealtimeConnectionError(
                f"Could not connect to GTFS-Realtime endpoint: {url}"
            ) from error

        except TimeoutError as error:
            raise GTFSRealtimeTimeoutError(
                f"GTFS-Realtime request timed out: {url}"
            ) from error

        if not data:
            raise ValueError(
                f"GTFS-Realtime endpoint returned an empty response: {url}"
            )

        logger.info("Retrieved GTFS-Realtime feed (%d bytes): %s", len(data), url)
        return data

    def fetch_vehicle_positions(self):
        return self.fetch(self.settings.vehicle_positions_url)

    def fetch_trip_updates(self):
        return self.fetch(self.settings.trip_updates_url)

    def fetch_service_alerts(self):
        return self.fetch(self.settings.service_alerts_url)

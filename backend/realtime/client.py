from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from backend.realtime.config import DEFAULT_COLLECTION_SETTINGS


class GTFSRealtimeClient:
    def __init__(self, settings=DEFAULT_COLLECTION_SETTINGS):
        self.settings = settings

    def fetch(self, url):
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
            raise RuntimeError(
                f"GTFS-Realtime request failed with HTTP {error.code}: {url}"
            ) from error

        except URLError as error:
            raise RuntimeError(
                f"Could not connect to GTFS-Realtime endpoint: {url}"
            ) from error

        if not data:
            raise ValueError(
                f"GTFS-Realtime endpoint returned an empty response: {url}"
            )

        return data

    def fetch_vehicle_positions(self):
        return self.fetch(self.settings.vehicle_positions_url)

    def fetch_trip_updates(self):
        return self.fetch(self.settings.trip_updates_url)

    def fetch_service_alerts(self):
        return self.fetch(self.settings.service_alerts_url)

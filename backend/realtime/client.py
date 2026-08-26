from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


BASE_URL = "https://gtfs.adelaidemetro.com.au/v1"

VEHICLE_POSITIONS_URL = f"{BASE_URL}/realtime/vehicle_positions"
TRIP_UPDATES_URL = f"{BASE_URL}/realtime/trip_updates"
SERVICE_ALERTS_URL = f"{BASE_URL}/realtime/service_alerts"


class GTFSRealtimeClient:
    def __init__(self, timeout=10):
        self.timeout = timeout

    def fetch(self, url):
        request = Request(
            url,
            headers={
                "User-Agent": "adelaide-metro-analysis/1.0"
            },
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
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
        return self.fetch(VEHICLE_POSITIONS_URL)

    def fetch_trip_updates(self):
        return self.fetch(TRIP_UPDATES_URL)

    def fetch_service_alerts(self):
        return self.fetch(SERVICE_ALERTS_URL)
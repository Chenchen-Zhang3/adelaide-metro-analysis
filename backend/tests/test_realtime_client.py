import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

from backend.realtime.client import (
    GTFSRealtimeClient,
    VEHICLE_POSITIONS_URL,
    TRIP_UPDATES_URL,
    SERVICE_ALERTS_URL,
)


class TestGTFSRealtimeClient(unittest.TestCase):

    @patch("backend.realtime.client.urlopen")
    def test_fetch_returns_bytes(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b"protobuf-data"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = GTFSRealtimeClient()
        result = client.fetch("https://example.com/feed")

        self.assertEqual(result, b"protobuf-data")

    @patch("backend.realtime.client.urlopen")
    def test_fetch_empty_response(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client = GTFSRealtimeClient()

        with self.assertRaises(ValueError):
            client.fetch("https://example.com/feed")

    @patch("backend.realtime.client.urlopen")
    def test_fetch_http_error(self, mock_urlopen):
        mock_urlopen.side_effect = HTTPError(
            url="https://example.com/feed",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=None,
        )

        client = GTFSRealtimeClient()

        with self.assertRaises(RuntimeError):
            client.fetch("https://example.com/feed")

    @patch("backend.realtime.client.urlopen")
    def test_fetch_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = URLError("Network unavailable")

        client = GTFSRealtimeClient()

        with self.assertRaises(RuntimeError):
            client.fetch("https://example.com/feed")

    @patch.object(GTFSRealtimeClient, "fetch")
    def test_named_feed_methods_use_correct_urls(self, mock_fetch):
        mock_fetch.return_value = b"data"

        client = GTFSRealtimeClient()

        client.fetch_vehicle_positions()
        mock_fetch.assert_called_with(VEHICLE_POSITIONS_URL)

        client.fetch_trip_updates()
        mock_fetch.assert_called_with(TRIP_UPDATES_URL)

        client.fetch_service_alerts()
        mock_fetch.assert_called_with(SERVICE_ALERTS_URL)


if __name__ == "__main__":
    unittest.main()
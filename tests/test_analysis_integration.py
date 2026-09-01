import json
import unittest
from pathlib import Path

from backend.analysis.metrics import (
    average_delay,
    delayed_service_count,
    delay_frequency,
    on_time_rate,
    early_arrival_rate,
    severe_delay_rate,
)
from backend.analysis.punctuality import classify_punctuality


ROOT = Path(__file__).resolve().parents[1]

TRIP_UPDATES_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "sample_trip_updates.json"
)


class TestAnalysisIntegration(unittest.TestCase):

    def load_trip_updates(self):
        with open(
            TRIP_UPDATES_PATH,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    def test_trip_update_delay_conversion(self):
        records = self.load_trip_updates()

        delays_minutes = [
            record["delay_seconds"] / 60
            for record in records
        ]

        self.assertEqual(
            delays_minutes,
            [6.0, 2.0]
        )

    def test_delay_metrics_from_shared_data(self):
        records = self.load_trip_updates()

        delays_minutes = [
            record["delay_seconds"] / 60
            for record in records
        ]

        self.assertEqual(
            average_delay(delays_minutes),
            4.0
        )

        self.assertEqual(
            delayed_service_count(delays_minutes),
            1
        )

        self.assertEqual(
            delay_frequency(delays_minutes),
            50.0
        )

        self.assertEqual(
            on_time_rate(delays_minutes),
            50.0
        )

        self.assertEqual(
            early_arrival_rate(delays_minutes),
            0.0
        )

        self.assertEqual(
            severe_delay_rate(delays_minutes),
            0.0
        )

    def test_punctuality_classification(self):
        records = self.load_trip_updates()

        delays_minutes = [
            record["delay_seconds"] / 60
            for record in records
        ]

        classifications = [
            classify_punctuality(delay)
            for delay in delays_minutes
        ]

        self.assertEqual(
            classifications,
            ["Delayed", "On Time"]
        )


if __name__ == "__main__":
    unittest.main()
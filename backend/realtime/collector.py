"""Scheduled collection for the existing GTFS-Realtime processing pipeline."""

import logging
from time import sleep

from backend.realtime.client import (
    GTFSRealtimeClient,
    GTFSRealtimeConnectionError,
    GTFSRealtimeHTTPError,
    GTFSRealtimeRequestError,
    GTFSRealtimeTimeoutError,
)
from backend.realtime.decoder import decode_feed
from backend.realtime.validation import (
    is_valid_trip_update,
    is_valid_vehicle_position,
)
from backend.services.gtfs_converter import (
    convert_trip_update,
    convert_vehicle_position,
)
from backend.services.historical_records import (
    prepare_trip_update_record,
    prepare_vehicle_position_record,
)


logger = logging.getLogger(__name__)


class GTFSRealtimeRetryExhaustedError(RuntimeError):
    """A recoverable feed request still failed after its configured retries."""


class GTFSRealtimeCollector:
    """Periodically fetch and process the supported GTFS-Realtime feeds.

    The collector coordinates existing components only: the HTTP client obtains
    bytes, the decoder creates a FeedMessage, and the converter creates the
    project's shared records. It retries temporary retrieval failures using the
    collection settings. Validation helpers reject missing entity fields before
    conversion; invalid entities/stop updates can be skipped independently.
    This layer returns records and does not write them to SQLite.
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

    def _is_retryable_error(self, error):
        if isinstance(
            error,
            (GTFSRealtimeConnectionError, GTFSRealtimeTimeoutError),
        ):
            return True

        if isinstance(error, GTFSRealtimeHTTPError):
            return (
                error.status_code in {408, 429}
                or error.status_code >= 500
            )

        return False

    def _fetch_with_retry(self, feed_name, fetch_feed):
        """Retry connection/timeouts and HTTP 408/429/5xx with a fixed delay.

        max_retry_attempts counts retries after the initial attempt. Permanent
        HTTP errors propagate immediately; decoding errors are outside this loop.
        """
        retry_attempt = 0

        while True:
            try:
                return fetch_feed()
            except GTFSRealtimeRequestError as error:
                if not self._is_retryable_error(error):
                    logger.error(
                        "Failed to retrieve %s feed without retry: %s",
                        feed_name,
                        error,
                    )
                    raise

                if retry_attempt >= self.client.settings.max_retry_attempts:
                    logger.error(
                        "Retries exhausted for %s feed after %d retry attempts: %s",
                        feed_name,
                        retry_attempt,
                        error,
                    )
                    raise GTFSRealtimeRetryExhaustedError(
                        "GTFS-Realtime request failed after "
                        f"{retry_attempt} retry attempts"
                    ) from error

                retry_attempt += 1
                logger.warning(
                    "Temporary failure retrieving %s feed; retrying attempt %d/%d: %s",
                    feed_name,
                    retry_attempt,
                    self.client.settings.max_retry_attempts,
                    error,
                )
                self.sleep_function(
                    self.client.settings.retry_delay_seconds
                )

    def _convert_vehicle_positions(self, feed):
        """Convert valid vehicle entities without stopping on an invalid one."""
        records = []
        skipped_entities = 0

        for entity in feed.entity:
            if not is_valid_vehicle_position(entity):
                skipped_entities += 1
                continue

            try:
                records.append(
                    prepare_vehicle_position_record(
                        convert_vehicle_position(entity)
                    )
                )
            except ValueError:
                skipped_entities += 1
                continue

        if skipped_entities:
            logger.warning(
                "Skipped %d invalid vehicle position entities",
                skipped_entities,
            )
        logger.info("Processed %d vehicle position records", len(records))
        return records

    def _convert_trip_updates(self, feed):
        """Convert valid trip entities without stopping on an invalid one."""
        records = []
        skipped_entities = 0

        for entity in feed.entity:
            if not is_valid_trip_update(entity):
                skipped_entities += 1
                continue

            try:
                records.extend(
                    prepare_trip_update_record(record)
                    for record in convert_trip_update(
                        entity,
                        self.stop_time_index,
                    )
                )
            except ValueError:
                skipped_entities += 1
                continue

        if skipped_entities:
            logger.warning("Skipped %d invalid trip update entities", skipped_entities)
        logger.info("Processed %d trip update records", len(records))
        return records

    def collect_once(self):
        """Return database-ready Vehicle Positions and Trip Updates lists.

        Feeds are fetched sequentially, so this is not an atomic upstream
        snapshot. A failed fetch/decode prevents this method returning a cycle;
        the persistence-aware scheduler decides whether to continue later.
        Service Alerts have no historical record contract and are not collected.
        """
        logger.info("Starting GTFS-Realtime collection cycle")
        vehicle_feed = self._decode_feed(
            "vehicle_positions",
            self._fetch_with_retry(
                "vehicle_positions",
                self.client.fetch_vehicle_positions,
            ),
        )
        trip_update_feed = self._decode_feed(
            "trip_updates",
            self._fetch_with_retry(
                "trip_updates",
                self.client.fetch_trip_updates,
            ),
        )

        result = {
            "vehicle_positions": self._convert_vehicle_positions(vehicle_feed),
            "trip_updates": self._convert_trip_updates(trip_update_feed),
        }
        logger.info(
            "Completed GTFS-Realtime collection cycle: %d vehicle position records, %d trip update records",
            len(result["vehicle_positions"]),
            len(result["trip_updates"]),
        )
        return result

    def _decode_feed(self, feed_name, data):
        """Decode a feed while retaining its collection context in failures."""
        try:
            return decode_feed(data)
        except (TypeError, ValueError) as error:
            logger.error("Failed to decode %s feed: %s", feed_name, error)
            raise

    def run(self, max_cycles=None):
        """Run collection cycles, waiting for the configured polling interval.

        ``max_cycles`` is optional for the long-running service and lets tests
        or command-line callers complete a known number of cycles.
        """
        completed_cycles = 0
        results = []

        while max_cycles is None or completed_cycles < max_cycles:
            try:
                results.append(self.collect_once())
            except GTFSRealtimeRetryExhaustedError:
                logger.warning(
                    "Skipping GTFS-Realtime collection cycle because feed retries were exhausted"
                )
            completed_cycles += 1

            if max_cycles is None or completed_cycles < max_cycles:
                self.sleep_function(
                    self.client.settings.polling_interval_seconds
                )

        return results

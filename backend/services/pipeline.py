import logging
import sqlite3
from datetime import datetime
from time import sleep

from backend.analysis.aggregation import prepare_analysis_output
from backend.database.repository import (
    get_trip_updates_filtered,
    persist_realtime_collection,
)
from backend.realtime.client import GTFSRealtimeRequestError
from backend.realtime.collector import (
    GTFSRealtimeRetryExhaustedError,
)


logger = logging.getLogger(__name__)


def persist_collection_result(collection_result):
    """Persist one collected realtime cycle as a single transaction."""

    # Get collected vehicle positions.
    vehicle_positions = collection_result.get(
        "vehicle_positions",
        [],
    )

    # Get collected trip updates.
    trip_updates = collection_result.get(
        "trip_updates",
        [],
    )

    # Delegate the database transaction to the repository layer.
    persistence_summary = persist_realtime_collection(
        vehicle_positions,
        trip_updates,
    )

    # Keep the established processed-count fields and expose transaction counts.
    return {
        "vehicle_positions_processed": len(vehicle_positions),
        "trip_updates_processed": len(trip_updates),
        **persistence_summary,
    }


def collect_and_persist(collector):
    """Collect one realtime cycle and store it."""

    # Collect one cycle of realtime data.
    collection_result = collector.collect_once()

    # Store the collected records.
    persistence_result = persist_collection_result(
        collection_result
    )

    # Return collection and persistence results.
    return {
        "collection_result": collection_result,
        "persistence_result": persistence_result,
    }


def run_collection_and_persist(
    collector,
    max_cycles=None,
    sleep_function=sleep,
    stop_event=None,
):
    """Continuously collect and store realtime data until stopped.

    Feed and SQLite failures make one collection cycle unsuccessful, but do not
    end the long-running historical collector. The next cycle still waits for
    the configured polling interval, avoiding a tight retry loop.

    Bounded runs return all successful results. Continuous runs retain only the
    latest successful result so feed payloads do not accumulate indefinitely.
    """

    # Reject an invalid cycle limit.
    if max_cycles is not None and max_cycles < 0:
        raise ValueError("max_cycles cannot be negative")

    # Track completed collection cycles.
    completed_cycles = 0

    # Store successful cycle results.
    results = []

    # Run until stopped or the cycle limit is reached.
    while (
        (max_cycles is None or completed_cycles < max_cycles)
        and (stop_event is None or not stop_event.is_set())
    ):
        cycle_number = completed_cycles + 1
        logger.info("Starting historical GTFS collection cycle %d", cycle_number)

        try:
            # Collect and persist one cycle.
            result = collect_and_persist(collector)

            # Unattended runs must not retain every historical feed in memory.
            if max_cycles is None:
                results[:] = [result]
            else:
                results.append(result)

            persistence_result = result["persistence_result"]
            logger.info(
                "Completed historical GTFS collection cycle %d: "
                "%d/%d vehicle positions; %d/%d trip updates stored and "
                "%d unchanged updates suppressed",
                cycle_number,
                persistence_result["vehicle_positions_inserted"],
                persistence_result["vehicle_positions_received"],
                persistence_result["trip_updates_inserted"],
                persistence_result["trip_updates_received"],
                persistence_result.get("trip_updates_suppressed", 0),
            )

        except GTFSRealtimeRetryExhaustedError:
            logger.warning(
                "Historical GTFS collection cycle %d skipped because feed "
                "retries were exhausted",
                cycle_number,
            )

        except GTFSRealtimeRequestError as error:
            logger.error(
                "Historical GTFS collection cycle %d failed while retrieving "
                "a feed: %s",
                cycle_number,
                error,
            )

        except (TypeError, ValueError) as error:
            logger.error(
                "Historical GTFS collection cycle %d failed while processing "
                "feed data: %s",
                cycle_number,
                error,
            )

        except sqlite3.Error as error:
            logger.error(
                "Historical GTFS collection cycle %d failed while persisting "
                "data; it was rolled back: %s",
                cycle_number,
                error,
            )

        # Mark the cycle as completed.
        completed_cycles += 1

        # Wait before the next collection cycle.
        if max_cycles is None or completed_cycles < max_cycles:
            polling_interval_seconds = (
                collector.client.settings.polling_interval_seconds
            )
            logger.info(
                "Waiting %d seconds before the next historical collection cycle",
                polling_interval_seconds,
            )
            if stop_event is not None:
                if stop_event.wait(polling_interval_seconds):
                    logger.info("Historical GTFS collection stop requested")
                    break
            else:
                sleep_function(polling_interval_seconds)

    # Return all successful cycle results.
    return results



def prepare_analysis_records(records):
    """Prepare database records for delay analysis."""

    from backend.analysis.punctuality import classify_punctuality

    latest_records = {}

    for index, record in enumerate(records):
        if (
            record.get("trip_id") is not None
            and record.get("scheduled_arrival") is not None
        ):
            key = (
                record["trip_id"],
                record["stop_id"],
                record["scheduled_arrival"],
            )
        else:
            # Keep legacy records separately when identity is unavailable.
            key = ("legacy_record", index)

        timestamp = record.get("timestamp")

        if key not in latest_records:
            latest_records[key] = record
        else:
            previous = latest_records[key]
            if (timestamp or "") >= (previous.get("timestamp") or ""):
                latest_records[key] = record

    analysis_records = []

    for record in latest_records.values():
        timestamp = record.get("timestamp")

        if timestamp:
            hour = datetime.fromisoformat(timestamp).hour

            if hour < 12:
                time_period = "Morning"
            elif hour < 17:
                time_period = "Afternoon"
            else:
                time_period = "Evening"
        else:
            time_period = "Unknown"

        delay_minutes = record["delay_seconds"] / 60

        analysis_records.append({
            "route_id": record["route_id"],
            "stop_id": record["stop_id"],
            "delay_minutes": delay_minutes,
            "punctuality_status": classify_punctuality(delay_minutes),
            "time_period": time_period,
            "data_type": "realtime_prediction",
        })

    return analysis_records


def query_and_analyse(
    route_id=None,
    stop_id=None,
    start_time=None,
    end_time=None,
        min_services=10,
):
    """Query stored records and prepare delay analysis."""

    # Query matching historical records.
    records = get_trip_updates_filtered(
        route_id=route_id,
        stop_id=stop_id,
        start_time=start_time,
        end_time=end_time,
    )

    # Prepare records for analysis.
    analysis_records = prepare_analysis_records(records)

    # Return aggregated analysis results.
    return prepare_analysis_output(
    analysis_records,
    min_services=min_services,
)
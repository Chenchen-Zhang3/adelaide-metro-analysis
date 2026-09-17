from datetime import datetime
from time import sleep

from backend.analysis.aggregation import prepare_analysis_output
from backend.database.repository import (
    get_trip_updates_filtered,
    persist_realtime_collection,
)
from backend.realtime.collector import (
    GTFSRealtimeRetryExhaustedError,
)


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
):
    """Continuously collect and store realtime data."""

    # Reject an invalid cycle limit.
    if max_cycles is not None and max_cycles < 0:
        raise ValueError("max_cycles cannot be negative")

    # Track completed collection cycles.
    completed_cycles = 0

    # Store successful cycle results.
    results = []

    # Run until stopped or the cycle limit is reached.
    while max_cycles is None or completed_cycles < max_cycles:
        try:
            # Collect and persist one cycle.
            result = collect_and_persist(collector)

            # Keep the successful cycle result.
            results.append(result)

        except GTFSRealtimeRetryExhaustedError:
            # Skip a cycle when temporary retries fail.
            pass

        # Mark the cycle as completed.
        completed_cycles += 1

        # Wait before the next collection cycle.
        if max_cycles is None or completed_cycles < max_cycles:
            sleep_function(
                collector.client.settings.polling_interval_seconds
            )

    # Return all successful cycle results.
    return results


def prepare_analysis_records(records):
    """Prepare database records for delay analysis."""

    # Store analysis-ready records.
    analysis_records = []

    for record in records:
        # Read the record timestamp.
        timestamp = record.get("timestamp")

        # Determine the time period.
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

        # Add the analysis record.
        analysis_records.append({
            "route_id": record["route_id"],
            "stop_id": record["stop_id"],
            "delay_minutes": record["delay_seconds"] / 60,
            "time_period": time_period,
        })

    # Return analysis-ready records.
    return analysis_records


def query_and_analyse(
    route_id=None,
    stop_id=None,
    start_time=None,
    end_time=None,
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
    return prepare_analysis_output(analysis_records)

"""Connect GTFS-Realtime collection results to the database."""

from datetime import datetime

from backend.analysis.aggregation import prepare_analysis_output
from backend.database.repository import (
    get_trip_updates_filtered,
    insert_trip_update,
    insert_vehicle_position,
)


def persist_collection_result(collection_result):
    """Store collected realtime records in the database."""

    vehicle_positions = collection_result.get(
        "vehicle_positions",
        []
    )

    trip_updates = collection_result.get(
        "trip_updates",
        []
    )

    # Store vehicle position records.
    for vehicle_position in vehicle_positions:
        insert_vehicle_position(vehicle_position)

    # Store trip update records.
    for trip_update in trip_updates:
        insert_trip_update(trip_update)

    return {
        "vehicle_positions_processed": len(vehicle_positions),
        "trip_updates_processed": len(trip_updates),
    }


def collect_and_persist(collector):
    """Collect realtime data and store it in the database."""

    # Collect one cycle of realtime data.
    collection_result = collector.collect_once()

    # Store the collected records.
    persistence_result = persist_collection_result(
        collection_result
    )

    return {
        "collection_result": collection_result,
        "persistence_result": persistence_result,
    }


def prepare_analysis_records(records):
    """Prepare database records for delay analysis."""

    analysis_records = []

    for record in records:
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

        analysis_records.append({
            "route_id": record["route_id"],
            "stop_id": record["stop_id"],
            "delay_minutes": record["delay_seconds"] / 60,
            "time_period": time_period,
        })

    return analysis_records


def query_and_analyse(
    route_id=None,
    stop_id=None,
    start_time=None,
    end_time=None,
):
    """Query stored records and prepare delay analysis."""

    records = get_trip_updates_filtered(
        route_id=route_id,
        stop_id=stop_id,
        start_time=start_time,
        end_time=end_time,
    )

    analysis_records = prepare_analysis_records(records)

    return prepare_analysis_output(analysis_records)
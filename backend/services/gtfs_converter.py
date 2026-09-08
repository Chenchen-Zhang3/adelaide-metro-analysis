from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from backend.realtime.validation import is_valid_stop_time_update


ADELAIDE_TIMEZONE = ZoneInfo("Australia/Adelaide")


def convert_stop(stop):
    return {
        "stop_id": str(stop["stop_id"]),
        "stop_name": str(stop["stop_name"]),
        "stop_lat": float(stop["stop_lat"]),
        "stop_lon": float(stop["stop_lon"]),
    }


def convert_route(route):
    return {
        "route_id": str(route["route_id"]),
        "route_short_name": str(route.get("route_short_name", "")),
        "route_long_name": str(route.get("route_long_name", "")),
        "route_type": int(route["route_type"]),
    }


def convert_trip(trip):
    return {
        "trip_id": str(trip["trip_id"]),
        "route_id": str(trip["route_id"]),
        "service_id": str(trip["service_id"]),
        "trip_headsign": str(trip.get("trip_headsign", "")),
        "direction_id": trip.get("direction_id"),
    }


def convert_stop_time(stop_time):
    return {
        "trip_id": str(stop_time["trip_id"]),
        "arrival_time": str(stop_time["arrival_time"]),
        "departure_time": str(stop_time["departure_time"]),
        "stop_id": str(stop_time["stop_id"]),
        "stop_sequence": int(stop_time["stop_sequence"]),
    }


def unix_timestamp_to_iso(timestamp):
    if not timestamp:
        return None

    return datetime.fromtimestamp(
        timestamp,
        tz=ADELAIDE_TIMEZONE
    ).isoformat()


def gtfs_time_to_datetime(service_date, gtfs_time):
    base_date = datetime.strptime(
        service_date,
        "%Y%m%d"
    ).replace(tzinfo=ADELAIDE_TIMEZONE)

    hours, minutes, seconds = map(
        int,
        gtfs_time.split(":")
    )

    return base_date + timedelta(
        hours=hours,
        minutes=minutes,
        seconds=seconds,
    )


def build_stop_time_index(stop_times):
    index = {}

    for stop_time in stop_times:
        key = (
            str(stop_time["trip_id"]),
            str(stop_time["stop_id"]),
            int(stop_time["stop_sequence"]),
        )

        index[key] = stop_time

    return index


def convert_vehicle_position(entity):
    if not entity.HasField("vehicle"):
        raise ValueError("Entity does not contain a vehicle position")

    vehicle = entity.vehicle

    if not vehicle.vehicle.id:
        raise ValueError("Vehicle position is missing vehicle_id")

    if not vehicle.HasField("position"):
        raise ValueError("Vehicle position is missing coordinates")

    result = {
        "vehicle_id": str(vehicle.vehicle.id),
        "trip_id": None,
        "route_id": None,
        "latitude": float(vehicle.position.latitude),
        "longitude": float(vehicle.position.longitude),
        "timestamp": unix_timestamp_to_iso(vehicle.timestamp),
    }

    if vehicle.HasField("trip"):
        if vehicle.trip.trip_id:
            result["trip_id"] = str(vehicle.trip.trip_id)

        if vehicle.trip.route_id:
            result["route_id"] = str(vehicle.trip.route_id)

    return result


def convert_trip_update(entity, stop_time_index):
    if not entity.HasField("trip_update"):
        raise ValueError("Entity does not contain a trip update")

    trip_update = entity.trip_update

    trip_id = str(trip_update.trip.trip_id)
    route_id = str(trip_update.trip.route_id)
    service_date = str(trip_update.trip.start_date)

    if not trip_id:
        raise ValueError("Trip update is missing trip_id")

    if not route_id:
        raise ValueError("Trip update is missing route_id")

    if not service_date:
        raise ValueError("Trip update is missing start_date")

    records = []

    for stop_update in trip_update.stop_time_update:
        if not is_valid_stop_time_update(stop_update):
            continue

        stop_id = str(stop_update.stop_id)
        stop_sequence = int(stop_update.stop_sequence)

        key = (
            trip_id,
            stop_id,
            stop_sequence,
        )

        scheduled_stop = stop_time_index.get(key)

        if scheduled_stop is None:
            continue

        scheduled_datetime = gtfs_time_to_datetime(
            service_date,
            scheduled_stop["arrival_time"],
        )

        actual_datetime = datetime.fromtimestamp(
            stop_update.arrival.time,
            tz=ADELAIDE_TIMEZONE,
        )

        delay_seconds = int(
            actual_datetime.timestamp()
            - scheduled_datetime.timestamp()
        )

        records.append({
            "trip_id": trip_id,
            "route_id": route_id,
            "stop_id": stop_id,
            "scheduled_arrival": scheduled_datetime.isoformat(),
            "actual_arrival": actual_datetime.isoformat(),
            "delay_seconds": delay_seconds,
            "timestamp": unix_timestamp_to_iso(
                trip_update.timestamp
            ),
        })

    return records

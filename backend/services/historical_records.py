"""Prepare validated GTFS-Realtime records for the database repository."""


def _required_string(record, field_name):
    value = record.get(field_name)

    if value is None or value == "":
        raise ValueError(f"Historical record is missing {field_name}")

    return str(value)


def _optional_string(record, field_name):
    value = record.get(field_name)

    if value is None or value == "":
        return None

    return str(value)


def prepare_vehicle_position_record(vehicle_position):
    """Map a validated Vehicle Position to the database insertion contract."""
    return {
        "vehicle_id": _required_string(vehicle_position, "vehicle_id"),
        "trip_id": _optional_string(vehicle_position, "trip_id"),
        "route_id": _optional_string(vehicle_position, "route_id"),
        "latitude": float(vehicle_position["latitude"]),
        "longitude": float(vehicle_position["longitude"]),
        "timestamp": _optional_string(vehicle_position, "timestamp"),
    }


def prepare_trip_update_record(trip_update):
    """Map a validated Trip Update to the database insertion contract."""
    return {
        "trip_id": _required_string(trip_update, "trip_id"),
        "route_id": _required_string(trip_update, "route_id"),
        "stop_id": _required_string(trip_update, "stop_id"),
        "scheduled_arrival": _optional_string(
            trip_update,
            "scheduled_arrival",
        ),
        "actual_arrival": _optional_string(trip_update, "actual_arrival"),
        "delay_seconds": int(trip_update["delay_seconds"]),
        "timestamp": _optional_string(trip_update, "timestamp"),
    }

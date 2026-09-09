"""Validation helpers for decoded GTFS-Realtime entities."""


def is_valid_vehicle_position(entity):
    """Return whether an entity contains the fields needed for conversion."""
    if not entity.HasField("vehicle"):
        return False

    vehicle = entity.vehicle

    return bool(vehicle.vehicle.id) and vehicle.HasField("position")


def is_valid_trip_update(entity):
    """Return whether a trip update has the identifiers needed for processing."""
    if not entity.HasField("trip_update"):
        return False

    trip_update = entity.trip_update

    if not trip_update.HasField("trip"):
        return False

    trip = trip_update.trip

    return bool(trip.trip_id and trip.route_id and trip.start_date)


def is_valid_stop_time_update(stop_update):
    """Return whether a stop update can be matched and used for delay data."""
    return (
        bool(stop_update.stop_id)
        and bool(stop_update.stop_sequence)
        and stop_update.HasField("arrival")
        and stop_update.arrival.HasField("time")
    )

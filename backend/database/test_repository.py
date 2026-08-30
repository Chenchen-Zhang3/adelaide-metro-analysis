from backend.database.models import create_tables
from backend.database.repository import (
    insert_stop,
    get_stop,
    insert_trip_update,
    get_trip_updates,
)


# Make sure all database tables exist
create_tables()


# ----------------------------
# Test 1: Insert and retrieve a stop
# ----------------------------

sample_stop = {
    "stop_id": "STOP_001",
    "stop_name": "Sample Adelaide Stop",
    "stop_lat": -34.9285,
    "stop_lon": 138.6007,
}

insert_stop(sample_stop)

result = get_stop("STOP_001")

print("Stop result:")
print(result)


# ----------------------------
# Test 2: Insert and retrieve a trip update
# ----------------------------

sample_trip_update = {
    "trip_id": "TRIP_001",
    "route_id": "ROUTE_001",
    "stop_id": "STOP_001",
    "scheduled_arrival": "2026-08-30T10:00:00",
    "actual_arrival": "2026-08-30T10:05:00",
    "delay_seconds": 300,
    "timestamp": "2026-08-30T10:05:00",
}

insert_trip_update(sample_trip_update)

updates = get_trip_updates("ROUTE_001")

print("\nTrip update results:")
print(updates)
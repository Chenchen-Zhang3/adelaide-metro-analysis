import json
from pathlib import Path

from backend.database.models import create_tables
from backend.database.repository import (
    insert_route,
    insert_stop,
    insert_trip,
    insert_stop_time,
    insert_trip_update,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load_json(filename):
    with open(FIXTURES / filename, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    create_tables()

    for stop in load_json("sample_stops.json"):
        insert_stop(stop)

    for route in load_json("sample_routes.json"):
        insert_route(route)

    for trip in load_json("sample_trips.json"):
        insert_trip(trip)

    for stop_time in load_json("sample_stop_times.json"):
        insert_stop_time(stop_time)

    for trip_update in load_json("sample_trip_updates.json"):
        insert_trip_update(trip_update)

    print("Sprint 3 integration database seeded successfully.")


if __name__ == "__main__":
    main()
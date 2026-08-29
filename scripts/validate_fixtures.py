import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]

SCHEMA_DIR = ROOT / "shared" / "schemas"
DATA_DIR = ROOT / "tests" / "fixtures"

PAIRS = {
    "stop.schema.json": "sample_stops.json",
    "route.schema.json": "sample_routes.json",
    "trip.schema.json": "sample_trips.json",
    "stop-time.schema.json": "sample_stop_times.json",
    "trip-update.schema.json": "sample_trip_updates.json",
    "vehicle.schema.json": "sample_vehicles.json",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def validate_schema_and_data():
    all_valid = True

    for schema_name, data_name in PAIRS.items():
        schema = load_json(SCHEMA_DIR / schema_name)
        data = load_json(DATA_DIR / data_name)

        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)

        for index, item in enumerate(data):
            errors = list(validator.iter_errors(item))

            if errors:
                all_valid = False
                print(f"FAIL: {data_name} item {index + 1}")

                for error in errors:
                    print(f"  - {error.message}")

        if all(not list(validator.iter_errors(item)) for item in data):
            print(f"PASS: {data_name}")

    return all_valid


def validate_references():
    stops = load_json(DATA_DIR / "sample_stops.json")
    routes = load_json(DATA_DIR / "sample_routes.json")
    trips = load_json(DATA_DIR / "sample_trips.json")
    stop_times = load_json(DATA_DIR / "sample_stop_times.json")
    trip_updates = load_json(DATA_DIR / "sample_trip_updates.json")
    vehicles = load_json(DATA_DIR / "sample_vehicles.json")

    stop_ids = {x["stop_id"] for x in stops}
    route_ids = {x["route_id"] for x in routes}
    trip_ids = {x["trip_id"] for x in trips}

    valid = True

    for trip in trips:
        if trip["route_id"] not in route_ids:
            print("FAIL: Invalid route reference in trips")
            valid = False

    for stop_time in stop_times:
        if stop_time["trip_id"] not in trip_ids:
            print("FAIL: Invalid trip reference in stop times")
            valid = False

        if stop_time["stop_id"] not in stop_ids:
            print("FAIL: Invalid stop reference in stop times")
            valid = False

    for update in trip_updates:
        if update["trip_id"] not in trip_ids:
            print("FAIL: Invalid trip reference in trip updates")
            valid = False

        if update["route_id"] not in route_ids:
            print("FAIL: Invalid route reference in trip updates")
            valid = False

        if update["stop_id"] not in stop_ids:
            print("FAIL: Invalid stop reference in trip updates")
            valid = False

    for vehicle in vehicles:
        if vehicle.get("trip_id") not in trip_ids:
            print("FAIL: Invalid trip reference in vehicles")
            valid = False

        if vehicle.get("route_id") not in route_ids:
            print("FAIL: Invalid route reference in vehicles")
            valid = False

    if valid:
        print("PASS: Cross-file GTFS references")

    return valid


if __name__ == "__main__":
    schema_ok = validate_schema_and_data()
    references_ok = validate_references()

    print()

    if schema_ok and references_ok:
        print("ALL SAMPLE GTFS DATA PASSED VALIDATION")
    else:
        print("VALIDATION FAILED")
        raise SystemExit(1)
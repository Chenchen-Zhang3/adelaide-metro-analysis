from pathlib import Path
import csv


def parse_stops(file_path):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"GTFS stops file not found: {file_path}")

    required_fields = {
        "stop_id",
        "stop_name",
        "stop_lat",
        "stop_lon",
    }

    stops = []

    with file_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError("stops.txt does not contain a header row")

        missing_fields = required_fields - set(reader.fieldnames)

        if missing_fields:
            raise ValueError(
                f"stops.txt is missing required fields: {sorted(missing_fields)}"
            )

        for row in reader:
            try:
                row["stop_lat"] = float(row["stop_lat"])
                row["stop_lon"] = float(row["stop_lon"])
            except (TypeError, ValueError):
                raise ValueError(
                    f"Invalid latitude or longitude for stop_id {row.get('stop_id')}"
                )

            stops.append(row)

    return stops


def parse_routes(file_path):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"GTFS routes file not found: {file_path}")

    required_fields = {
        "route_id",
        "route_short_name",
        "route_long_name",
        "route_type",
    }

    routes = []

    with file_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError("routes.txt does not contain a header row")

        missing_fields = required_fields - set(reader.fieldnames)

        if missing_fields:
            raise ValueError(
                f"routes.txt is missing required fields: {sorted(missing_fields)}"
            )

        for row in reader:
            try:
                row["route_type"] = int(row["route_type"])
            except (TypeError, ValueError):
                raise ValueError(
                    f"Invalid route_type for route_id {row.get('route_id')}"
                )

            routes.append(row)

    return routes



def parse_trips(file_path):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"GTFS trips file not found: {file_path}")

    required_fields = {
        "route_id",
        "service_id",
        "trip_id",
    }

    trips = []

    with file_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError("trips.txt does not contain a header row")

        missing_fields = required_fields - set(reader.fieldnames)

        if missing_fields:
            raise ValueError(
                f"trips.txt is missing required fields: {sorted(missing_fields)}"
            )

        for row in reader:
            if row.get("direction_id"):
                try:
                    row["direction_id"] = int(row["direction_id"])
                except ValueError:
                    raise ValueError(
                        f"Invalid direction_id for trip_id {row.get('trip_id')}"
                    )
            else:
                row["direction_id"] = None

            if row.get("wheelchair_accessible"):
                try:
                    row["wheelchair_accessible"] = int(
                        row["wheelchair_accessible"]
                    )
                except ValueError:
                    raise ValueError(
                        f"Invalid wheelchair_accessible value for trip_id "
                        f"{row.get('trip_id')}"
                    )
            else:
                row["wheelchair_accessible"] = None

            trips.append(row)

    return trips

def parse_stop_times(file_path):
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"GTFS stop_times file not found: {file_path}"
        )

    required_fields = {
        "trip_id",
        "arrival_time",
        "departure_time",
        "stop_id",
        "stop_sequence",
    }

    stop_times = []

    with file_path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(
                "stop_times.txt does not contain a header row"
            )

        missing_fields = required_fields - set(reader.fieldnames)

        if missing_fields:
            raise ValueError(
                f"stop_times.txt is missing required fields: "
                f"{sorted(missing_fields)}"
            )

        for row in reader:
            try:
                row["stop_sequence"] = int(row["stop_sequence"])
            except (TypeError, ValueError):
                raise ValueError(
                    f"Invalid stop_sequence for "
                    f"trip_id {row.get('trip_id')}"
                )

            stop_times.append(row)

    return stop_times

# GTFS Processing Approach

## Overview

The backend processes both Adelaide Metro static GTFS data and GTFS-Realtime feeds.

The current processing flow is:

Static GTFS files
→ Static GTFS parser
→ Shared data format

GTFS-Realtime API
→ Realtime client
→ Protobuf decoder
→ Shared data format

Static stop times and realtime trip updates are also combined to calculate service delay.

---

## Static GTFS Processing

Static GTFS data is processed by:

`backend/parsers/static_gtfs.py`

The parser currently supports:

- `stops.txt`
- `routes.txt`
- `trips.txt`
- `stop_times.txt`

GTFS identifiers such as `stop_id`, `route_id` and `trip_id` are kept as strings.

Numeric values such as coordinates, route type and stop sequence are converted to appropriate Python numeric types.

Required columns are validated before records are processed.

GTFS service times are kept as strings because GTFS times may exceed 24:00, for example `24:56:02`.

---

## GTFS-Realtime Processing

Realtime data is accessed through:

`backend/realtime/client.py`

The client accesses the Adelaide Metro GTFS-Realtime feeds for:

- Vehicle Positions
- Trip Updates
- Service Alerts

The API responses are returned as raw protobuf bytes.

These bytes are decoded by:

`backend/realtime/decoder.py`

The decoder converts the protobuf response into a GTFS-Realtime `FeedMessage`.

---

## Shared Data Conversion

Processed GTFS data is converted to the agreed project data structure by:

`backend/services/gtfs_converter.py`

The converter currently supports:

- Stops
- Routes
- Trips
- Stop Times
- Vehicle Positions
- Trip Updates

The output follows the schemas defined in:

`shared/schemas/`

Realtime timestamps are converted to ISO 8601 format using the Adelaide timezone.

---

## Delay Calculation

Adelaide Metro realtime trip updates provide actual arrival timestamps.

Static `stop_times.txt` provides the scheduled arrival time.

The backend matches records using:

- `trip_id`
- `stop_id`
- `stop_sequence`

The scheduled GTFS time is combined with the realtime trip `start_date`.

GTFS times greater than 24 hours are supported. For example:

`20260829 + 24:56:02`

is interpreted as:

`2026-08-30T00:56:02+09:30`

Delay is calculated as:

`delay_seconds = actual_arrival - scheduled_arrival`

The processed trip update then contains:

- trip ID
- route ID
- stop ID
- scheduled arrival
- actual arrival
- delay in seconds
- realtime timestamp

---

## Testing

Backend unit tests are stored in:

`backend/tests/`

The current test suite covers:

- Static GTFS parsing
- Required field validation
- GTFS-Realtime HTTP client behaviour
- Realtime protobuf decoding
- Shared data conversion
- GTFS times greater than 24:00
- Stop-time indexing
- Vehicle position conversion
- Trip update conversion and delay calculation

The full backend test suite can be run with:

```bash
python -m unittest discover -s backend/tests -p "test_*.py" -v
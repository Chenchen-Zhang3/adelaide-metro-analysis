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

### Collection configuration

Collection parameters are centralised in `backend/realtime/config.py`.
`GTFSRealtimeCollectionSettings` defines the three feed URLs, request timeout,
polling interval, retry settings and HTTP user agent. The default polling
interval is 60 seconds, the request timeout is 10 seconds, and the collector
may retry a temporary failure twice with a five-second retry delay.

The realtime client receives these settings rather than hard-coding collection
parameters. This allows a future scheduled collector to use the same polling
policy without changing the existing fetch, decoding or conversion logic.

The API responses are returned as raw protobuf bytes.

These bytes are decoded by:

`backend/realtime/decoder.py`

The decoder converts the protobuf response into a GTFS-Realtime `FeedMessage`.

### Scheduled collection

`backend/realtime/collector.py` provides `GTFSRealtimeCollector`. One
collection cycle fetches the supported Vehicle Positions and Trip Updates feeds,
decodes their raw protobuf bytes, and passes their entities to the existing
shared-data converters. It returns processed records for the next persistence
step; it does not write to the database itself.

`run()` repeats this collection cycle using
`GTFSRealtimeCollectionSettings.polling_interval_seconds`. The optional
`max_cycles` argument makes scheduled behaviour testable without waiting for a
live feed or a real timer. Record-level validation is intentionally left to a
separate Sprint 2 task.

### Resilient feed retrieval

The collector retries a connection failure, timeout, or temporary HTTP response
(408, 429, or a 5xx status) using the configured retry delay. Permanent HTTP
errors, such as 403, fail immediately rather than repeatedly requesting the
feed. When the retries for a temporary failure are exhausted, that collection
cycle is skipped and the scheduled collector proceeds to its next cycle.

### Record validation and missing-data handling

`backend/realtime/validation.py` validates decoded entities before conversion.
Vehicle Positions require a vehicle ID and position; trip and route identifiers
remain optional for Vehicle Positions because the shared schema permits them to
be `null`. Trip Updates require a trip ID, route ID and start date because the
existing delay conversion needs all three.

Incomplete stop-time updates are skipped when they lack a stop ID, stop
sequence or arrival time. The collector processes records entity-by-entity, so
an invalid entity is skipped while valid entities in the same feed continue to
be converted.

### Historical database handoff

`backend/services/historical_records.py` maps validated converter output to the
plain-dictionary contract accepted by the database repository. Vehicle Position
records contain `vehicle_id`, optional `trip_id` and `route_id`, `latitude`,
`longitude`, and an optional ISO 8601 `timestamp`. Trip Update records contain
`trip_id`, `route_id`, `stop_id`, optional arrival timestamps, integer
`delay_seconds`, and an optional ISO 8601 `timestamp`.

The adapter normalises missing optional values to `None`, preserves identifier
strings and numeric fields, and does not insert data itself. The caller can pass
its output directly to `insert_vehicle_position()` or `insert_trip_update()`.

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
- Realtime record validation and invalid-record skipping
- Historical record handoff and database repository compatibility
- Shared data conversion
- GTFS times greater than 24:00
- Stop-time indexing
- Vehicle position conversion
- Trip update conversion and delay calculation

The full backend test suite can be run with:

```bash
python -m unittest discover -s backend/tests -p "test_*.py" -v

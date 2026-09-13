# GTFS Processing Approach

## Overview

The backend processes both Adelaide Metro static GTFS data and GTFS-Realtime feeds.

The current processing flow is:

Static GTFS files
→ Static GTFS parser
→ Shared data format

GTFS-Realtime API
→ Collection configuration and scheduled collector
→ Retry-aware realtime client
→ Protobuf decoder and record validation
→ GTFS conversion and timestamp/delay processing
→ Database-ready historical records
→ Persistence layer

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
parameters. The scheduled collector uses the same polling and retry policy
without changing existing fetch, decoding or conversion logic.

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
live feed or a real timer. It processes Vehicle Positions and Trip Updates;
Service Alerts do not yet have a historical record or persistence contract.

### Resilient feed retrieval

The collector retries a connection failure, timeout, or temporary HTTP response
(408, 429, or a 5xx status) using the configured retry delay. Permanent HTTP
errors, such as 403, fail immediately rather than repeatedly requesting the
feed. When the retries for a temporary failure are exhausted, that collection
cycle is skipped and the scheduled collector proceeds to its next cycle.

### Runtime logging

The realtime pipeline uses Python's standard `logging` module. Each module
creates a named logger with `logging.getLogger(__name__)`; handler and output
format configuration remain the responsibility of the application that runs the
collector.

Collection-cycle start, successful retrieval, processed record counts and cycle
completion are logged at `INFO`. Temporary retrieval failures and invalid
entities that are skipped are logged at `WARNING`. Retry exhaustion,
non-retryable request failures and decode failures are logged at `ERROR`.
Raw protobuf payloads are never logged.

| Problem | Actual behaviour |
| --- | --- |
| Connection, timeout, 408, 429 or 5xx failure | Retry using the configured limit and delay |
| Permanent HTTP failure | Log and propagate without retry |
| Retry exhausted in `collect_once()` | Log and raise `GTFSRealtimeRetryExhaustedError` |
| Retry exhausted in `run()` | Log, skip the failed cycle and continue scheduling |
| Invalid entity or conversion `ValueError` | Skip that entity and continue the feed |
| Missing stop-time match or arrival | Produce no delay record for that stop update |
| Empty decoded feed | Return empty record lists |

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

#### Vehicle Position handoff contract

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `vehicle_id` | `str` | Yes | GTFS vehicle identifier |
| `trip_id` | `str` or `None` | No | Associated trip when supplied by the feed |
| `route_id` | `str` or `None` | No | Associated route when supplied by the feed |
| `latitude` | `float` | Yes | Vehicle latitude |
| `longitude` | `float` | Yes | Vehicle longitude |
| `timestamp` | ISO 8601 `str` or `None` | No | Vehicle timestamp in Adelaide time |

#### Trip Update handoff contract

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `trip_id` | `str` | Yes | GTFS trip identifier |
| `route_id` | `str` | Yes | GTFS route identifier |
| `stop_id` | `str` | Yes | Matched GTFS stop identifier |
| `scheduled_arrival` | ISO 8601 `str` or `None` | No | Scheduled Adelaide arrival time |
| `actual_arrival` | ISO 8601 `str` or `None` | No | Realtime arrival used for delay calculation |
| `delay_seconds` | `int` | Yes | Raw actual-minus-scheduled delay |
| `timestamp` | ISO 8601 `str` or `None` | No | Trip Update message timestamp in Adelaide time |

The repository functions in `backend/database/repository.py` accept these
dictionaries directly. Optional values are read with `.get(...)`, preserving
the `None` convention as SQL `NULL`.

### Integrated processing workflow

`backend/realtime/pipeline.py` provides the reusable
`GTFSRealtimeProcessingPipeline` entry point. It coordinates the existing
configured client, collector, retry policy, decoder, validators, converters,
historical-record mappers and logging without duplicating those components.

```python
from backend.realtime.pipeline import GTFSRealtimeProcessingPipeline

pipeline = GTFSRealtimeProcessingPipeline(stop_time_index=stop_time_index)
records = pipeline.process_once()
```

Constructor dependencies are optional `client`, `stop_time_index` and
`sleep_function`. `process_once()` retrieves and processes one collection cycle
and returns:

```python
{
    "vehicle_positions": [vehicle_record, ...],
    "trip_updates": [trip_update_record, ...],
}
```

`run(max_cycles=None)` delegates to scheduled collection and returns successful
cycle results. The realtime processing subsystem ends when these database-ready
records are returned; it does not insert them itself.

The persistence layer begins with `insert_vehicle_position()` and
`insert_trip_update()`. The wider `backend/services/pipeline.py` integration
service also exposes `persist_collection_result(collection_result)` to insert
both record lists and return processed counts. Database querying, analysis, API
and frontend integration remain outside this realtime subsystem.

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

`build_stop_time_index(stop_times)` creates the static lookup used for this
match. Its key is `(trip_id, stop_id, stop_sequence)`. Build the index once and
inject it into `GTFSRealtimeProcessingPipeline` or `GTFSRealtimeCollector` so
that it can be reused across cycles rather than rebuilt for every entity.

The scheduled GTFS time is combined with the realtime trip `start_date`.

GTFS times greater than 24 hours are supported. For example:

`20260829 + 24:56:02`

is interpreted as:

`2026-08-30T00:56:02+09:30`

Delay is calculated as:

`delay_seconds = actual_arrival - scheduled_arrival`

Both values are timezone-aware Adelaide datetimes. GTFS service times may be
greater than 24:00 and are carried into the following calendar day while
retaining their original service date context. A negative `delay_seconds` is
preserved for an early arrival and zero is preserved for an exactly scheduled
arrival; classification belongs to the analysis module.

Missing actual arrival data or a missing static stop-time match does not create
a guessed delay record. Unix timestamps are converted using
`ZoneInfo("Australia/Adelaide")`, so daylight-saving offsets are applied rather
than hard-coded.

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
- Configurable polling, bounded retry and scheduled collection behaviour
- Shared data conversion
- GTFS times greater than 24:00
- Stop-time indexing
- Vehicle position conversion
- Trip update conversion and delay calculation
- Realtime logging behaviour
- End-to-end pipeline processing with synthetic protobuf feeds
- Temporary SQLite compatibility between pipeline output and repository inserts

The full backend test suite can be run with:

```bash
python -m unittest discover -s backend/tests -p "test_*.py" -v
```

The focused realtime pipeline tests can be run with:

```bash
python -m unittest backend.tests.test_realtime_processing_pipeline -v
```

Tests use synthetic `FeedMessage` values, `MagicMock` clients and injected
sleep functions. They do not call the live Adelaide Metro API, wait for real
polling intervals or write to a production database. Pipeline-to-repository
compatibility uses a temporary SQLite database.

At the Sprint 2 Task 9 verification, the relevant GTFS processing suite ran 57
tests successfully. Full backend discovery found 64 tests: 62 passed and two
test modules could not load locally because `Flask` and `pytest` were not
installed. `Flask` is listed in `requirements.txt`; `pytest` is used by
`backend/tests/test_database_repository.py` and must currently be installed
separately for that module.

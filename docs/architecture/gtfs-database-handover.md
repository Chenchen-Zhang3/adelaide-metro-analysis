# GTFS-Realtime to Database Handover

## Scope

This document records the SCRUM-185 verification of the existing GTFS-Realtime
processing and SQLite persistence boundary. It complements, rather than
repeats, the processing detail in [GTFS Processing Approach](gtfs-processing.md)
and the table/query reference in [Database and Query Interface](../database_query_interface.md).

## Verified flow

```text
Adelaide Metro GTFS-Realtime feed
  -> GTFSRealtimeClient
  -> GTFSRealtimeCollector (retry, decode, validate and convert)
  -> GTFSRealtimeProcessingPipeline.process_once()
  -> database-ready dictionaries
  -> backend.services.pipeline.persist_collection_result()
  -> one repository transaction for the collection cycle
  -> SQLite
```

`GTFSRealtimeProcessingPipeline.process_once()` is the reusable processing
entry point. It returns a dictionary with `vehicle_positions` and
`trip_updates` lists. `persist_collection_result()` is the system-integration
handover point: it passes each dictionary unchanged to the repository's
collection-cycle transaction and returns attempted and inserted record counts.

The current client and decoder were also checked against the live Adelaide
Metro Vehicle Positions and Trip Updates feeds. The deterministic automated
test uses synthetic protobuf feeds and a temporary SQLite database so that it
does not depend on a live feed or modify the development database.

## Vehicle Position contract

Pass each output dictionary to:

```python
insert_vehicle_position(record)
```

| Field | Type | Required | SQLite column |
| --- | --- | --- | --- |
| `vehicle_id` | `str` | Yes | `vehicle_id TEXT NOT NULL` |
| `trip_id` | `str` or `None` | No | `trip_id TEXT` |
| `route_id` | `str` or `None` | No | `route_id TEXT` |
| `latitude` | `float` | Yes | `latitude REAL NOT NULL` |
| `longitude` | `float` | Yes | `longitude REAL NOT NULL` |
| `timestamp` | ISO 8601 `str` with Adelaide offset, or `None` | No | `timestamp TEXT` |

## Trip Update / delay contract

Pass each output dictionary to:

```python
insert_trip_update(record)
```

| Field | Type | Required | SQLite column |
| --- | --- | --- | --- |
| `trip_id` | `str` | Yes | `trip_id TEXT NOT NULL` |
| `route_id` | `str` | Yes | `route_id TEXT NOT NULL` |
| `stop_id` | `str` | Yes | `stop_id TEXT NOT NULL` |
| `scheduled_arrival` | ISO 8601 `str` with Adelaide offset | Yes | Converted to `scheduled_arrival INTEGER` |
| `actual_arrival` | ISO 8601 `str` with Adelaide offset, or `None` | No | Validated, then derived rather than stored |
| `delay_seconds` | `int` | Yes | `delay_seconds INTEGER NOT NULL` |
| `timestamp` | ISO 8601 `str` with Adelaide offset, or `None` | No | Converted to `observed_at INTEGER` |

`delay_seconds` is the signed raw value `actual_arrival - scheduled_arrival`.
Negative values (early) and zero (on time) are retained; classification belongs
to analysis, not persistence.

Repository queries reconstruct `actual_arrival` and return Adelaide ISO-8601
timestamps, preserving the application-facing contract while the physical
schema uses compact UTC epoch seconds. Unchanged prediction states are
suppressed between periodic checkpoints; see
`historical-storage-optimisation.md`.

## Static GTFS dependency

Trip Update delay records require a static stop-time match. Build
`stop_time_index` once from parsed `stop_times` using
`build_stop_time_index(stop_times)`, then inject it into
`GTFSRealtimeProcessingPipeline` (or its collector) and reuse it for each
collection cycle. The key is `(trip_id, stop_id, stop_sequence)`.

All realtime Unix timestamps are converted with `ZoneInfo("Australia/Adelaide")`
before handover. Scheduled GTFS times above `24:00:00` are combined with the
service date and correctly roll into the following calendar day. A missing
stop-time match or arrival timestamp produces no guessed Trip Update delay
record.

## Responsibility boundary

| Concern | Owner | Behaviour at the boundary |
| --- | --- | --- |
| Feed requests and transient request retries | `GTFSRealtimeClient` / `GTFSRealtimeCollector` | A retry-exhausted cycle is skipped by scheduled collection. |
| Feed/entity and converter validation | `backend.realtime.validation`, converters and `historical_records` | Invalid or incomplete entities are skipped; valid entities in the same feed continue. |
| Record-to-database handover | `persist_collection_result()` | Delegates the two database-ready lists without changing their fields. |
| Duplicate/change handling | Repository state table plus SQLite unique index | First, changed, checkpoint and reappearance states are stored; unchanged states are suppressed. |
| Database errors and transaction policy | Repository/application integration layer | One transaction spans both record lists; SQLite failures are logged, rolled back and re-raised to the caller. |

The processing pipeline must not retry database errors or implement a second
change-detection scheme. A collection cycle containing invalid realtime entities
can still persist its valid records. A SQLite persistence failure rolls back
the whole collection-cycle transaction and remains visible to the caller.

## SCRUM-186 persistence behaviour

`persist_realtime_collection()` begins one SQLite transaction for a completed
collection cycle. Vehicle Positions retain unique-index protection. Trip
Updates are compared with persisted current state and classified as initial,
changed, checkpoint, reappearance or suppressed before the transaction commits.
The summary exposes stored and suppressed counts without labelling semantic
suppression as a SQL duplicate.

Connection/setup, Vehicle Position, Trip Update and commit failures are logged
with their stage, trigger a rollback where a transaction exists, and preserve
the original SQLite exception. `run_collection_and_persist()` therefore cannot
mistake a failed database write for a successful collection cycle.

SQLite remains the configured database. Its path defaults to
`backend/database/adelaide_metro.db`, but an application can set
`ADELAIDE_METRO_DATABASE_PATH` before startup to select another path without
placing configuration in GTFS business logic. `create_tables()` remains
idempotent through `IF NOT EXISTS`; repeat initialisation preserves historical
rows and duplicate-protection indexes.

## SCRUM-187 continuous runtime

SCRUM-187 adds the startup lifecycle and reuses this C02 transaction boundary
for every scheduled cycle. The runner builds the static stop-time index once at
application startup, reuses it until restart, and passes the existing collector
to the persistence-aware scheduler. See [Continuous Historical GTFS Collection
Runner](historical-collection-runner.md) for the command, recovery policy and
hosting limitation.

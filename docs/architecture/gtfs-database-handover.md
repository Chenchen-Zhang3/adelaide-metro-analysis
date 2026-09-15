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
  -> insert_vehicle_position() / insert_trip_update()
  -> SQLite
```

`GTFSRealtimeProcessingPipeline.process_once()` is the reusable processing
entry point. It returns a dictionary with `vehicle_positions` and
`trip_updates` lists. `persist_collection_result()` is the system-integration
handover point: it passes each dictionary unchanged to the matching repository
insert function and returns the attempted record counts.

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
| `scheduled_arrival` | ISO 8601 `str` with Adelaide offset, or `None` | No | `scheduled_arrival TEXT` |
| `actual_arrival` | ISO 8601 `str` with Adelaide offset, or `None` | No | `actual_arrival TEXT` |
| `delay_seconds` | `int` | Yes | `delay_seconds INTEGER NOT NULL` |
| `timestamp` | ISO 8601 `str` with Adelaide offset, or `None` | No | `timestamp TEXT` |

`delay_seconds` is the signed raw value `actual_arrival - scheduled_arrival`.
Negative values (early) and zero (on time) are retained; classification belongs
to analysis, not persistence.

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
| Record-to-database handover | `persist_collection_result()` | Iterates the two database-ready lists without changing their fields. |
| Duplicate handling | SQLite repository unique indexes plus `INSERT OR IGNORE` | Duplicate rows are ignored at insertion. |
| Database errors and transaction policy | Repository/application integration layer | Current insert methods commit one record at a time and propagate database errors; no batch transaction interface exists. |

The processing pipeline must not retry database errors or implement a second
deduplication scheme. A collection cycle containing invalid realtime entities
can still persist its valid records. A database insertion failure is not
currently isolated per record or per cycle.

## Current status and SCRUM-186

The existing processing records, shared JSON schemas and SQLite repository
input shapes match; SCRUM-185 required no production field/type changes.

SCRUM-186 can build on `collect_and_persist()` or
`run_collection_and_persist()` to implement the next agreed persistence
behaviour. Before introducing a production writer, decide whether it needs
batch transactions, per-record database-error handling, operational database
configuration/migrations, and live static-GTFS index refresh. These are
database/runtime concerns and are deliberately outside this handover contract.

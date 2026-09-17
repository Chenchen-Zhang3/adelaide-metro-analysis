# Sprint 3 Database Integration Test Report

## Overview

This report records the Sprint 3 integration testing for the historical
database and real Adelaide Metro GTFS-Realtime data.

The testing verifies that real GTFS-Realtime records can be processed,
persisted to SQLite, retained across multiple collection cycles, and queried
using the database repository interfaces.

## Real GTFS-Realtime Collection

A local historical database was used for live integration testing:

```text
data/history/adelaide_metro_history.db
```
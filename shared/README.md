# Shared Resources

This directory contains common definitions used by multiple modules in
the Adelaide Metro Analysis project.

## Structure

### schemas/

Contains shared data schemas used to define the expected structure of
GTFS and processed transport data.

Current schemas:

- `stop.schema.json`
- `route.schema.json`
- `trip.schema.json`
- `trip-update.schema.json`
- `vehicle.schema.json`
- `stop-time.schema.json`
- `recorded-route-map.schema.json` — recorded demo GeoJSON plus trip/stop relationships.

### constants/

Reserved for constants shared between modules.

### types/

Reserved for common application data types.

## Integration Rule

Modules exchanging data should follow the shared schemas and preserve
common GTFS identifiers such as:

- `stop_id`
- `route_id`
- `trip_id`
- `vehicle_id`

Changes to shared structures should be reviewed before integration into
the main branch.

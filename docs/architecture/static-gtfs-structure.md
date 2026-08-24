# Adelaide Metro Static GTFS Structure Investigation

## 1. Purpose

This investigation examines the structure of the Adelaide Metro static GTFS dataset before implementing the static GTFS parser. The initial parser will focus on stops, routes and trips, while related GTFS files are also reviewed to understand how the data is connected.

## 2. Data Source

- Dataset version: `1692`
- Retrieval date: 23 August 2026
- Adelaide Metro GTFS: https://gtfs.adelaidemetro.com.au/#/gtfsr
- GTFS specification: https://gtfs.org/

The static GTFS dataset was obtained from the official Adelaide Metro GTFS service recommended by the client.

The client also recommended MobilityData/GTFS.org as the appropriate reference for the current GTFS specification.

## 3. Files Observed

The downloaded Adelaide Metro static GTFS dataset contains the following files:

- agency.txt
- booking_rules.txt
- calendar_dates.txt
- calendar.txt
- feed_info.txt
- Release Notes.txt
- routes.txt
- shapes.txt
- stop_times.txt
- stops.txt
- transfers.txt
- trips.txt

The core files investigated for the initial backend implementation are:

- stops.txt
- routes.txt
- trips.txt
- stop_times.txt

## 4. Core GTFS Files

### 4.1 stops.txt

`stops.txt` defines public transport stops and stations.

Observed fields:

- stop_id
- stop_code
- stop_name
- stop_desc
- stop_lat
- stop_lon
- zone_id
- stop_url
- location_type
- parent_station
- stop_timezone
- wheelchair_boarding

Important fields for the project include:

- `stop_id` – unique identifier used to link stops with stop times
- `stop_name` – user-facing stop name
- `stop_lat` – latitude used for map visualisation
- `stop_lon` – longitude used for map visualisation
- `stop_code` – public stop identifier

Example:

- stop_id: 100799
- stop_code: 17894
- stop_name: Stop School / Zone A Glenunga International High School Conyngham St
- latitude: -34.949104
- longitude: 138.634403

### 4.2 routes.txt

`routes.txt` defines public transport routes/services.

Observed fields:

- route_id
- agency_id
- route_short_name
- route_long_name
- route_desc
- route_type
- route_url
- route_color
- route_text_color
- RouteGroup

Important observations:

- Route identifiers are not always numeric. Examples include values such as `100E`, `100N` and `BEL`.
- Route IDs should therefore be handled as strings by the parser.
- `route_type` identifies the transport mode.
- Route colour information may later be useful for map visualisation.
- `RouteGroup` appears to be an Adelaide Metro-specific grouping field and should not be relied on until its behaviour is confirmed.

### 4.3 trips.txt

`trips.txt` defines individual scheduled journeys belonging to a route.

Observed fields:

- route_id
- service_id
- trip_id
- trip_headsign
- trip_short_name
- direction_id
- block_id
- shape_id
- wheelchair_accessible

A route may contain many individual trips.

Example:

- route_id: 870
- service_id: 22
- trip_id: 224061
- trip_headsign: City (School Bus)
- direction_id: 1
- block_id: 11350
- shape_id: 9202
- wheelchair_accessible: 1

Some fields, such as `trip_short_name`, may be empty and must therefore be treated as optional.

### 4.4 stop_times.txt

`stop_times.txt` connects trips to stops and provides the scheduled arrival and departure times for each stop visited by a trip.

Observed fields:

- trip_id
- arrival_time
- departure_time
- stop_id
- stop_sequence
- stop_headsign
- pickup_type
- drop_off_type
- shape_dist_traveled
- timepoint
- pickup_booking_rule_id
- drop_off_booking_rule_id

The `trip_id` links to `trips.txt`, while `stop_id` links to `stops.txt`.

The `stop_sequence` field defines the order in which stops are visited. The Adelaide Metro dataset contains non-consecutive values such as `999`, so the parser must not assume that stop sequences always increase by one.

## 5. Core Data Relationships

The main relationship between the static GTFS files is:

routes.txt
→ route_id
→ trips.txt
→ trip_id
→ stop_times.txt
→ stop_id
→ stops.txt

A real record was checked to validate this relationship:

- Route 870 contains Trip 224061.
- Trip 224061 has the headsign "City (School Bus)".
- The first stop-time record for Trip 224061 references Stop 100799.
- Stop 100799 corresponds to Glenunga International High School on Conyngham Street.

This confirms that route, trip, schedule and stop information can be joined using the GTFS identifier fields.

## 6. Supporting GTFS Files

Other files provide additional information that may be required in later development:

- `agency.txt` – operator/agency information
- `calendar.txt` and `calendar_dates.txt` – service operating dates
- `shapes.txt` – geographical route shapes
- `booking_rules.txt` – booking requirements for applicable services
- `transfers.txt` – transfer information between stops

These files are not part of the initial parser task but may be required for later route analysis, map visualisation and timetable processing.

## 7. Parser Considerations

The investigation identified several requirements for the static GTFS parser:

1. GTFS identifier fields should generally be preserved as strings.
2. Optional and empty fields must be handled safely.
3. The parser should validate required columns before processing a file.
4. `stop_sequence` values should be used for ordering but must not be assumed to be consecutive.
5. GTFS arrival and departure times should initially be preserved in GTFS time format rather than treated as normal clock times without validation.
6. The parser should keep the raw GTFS meaning separate from the project's agreed shared data format.

## 8. Relevance to the Project

The static GTFS structure provides the foundation for several project requirements:

- displaying Adelaide Metro stops on the map
- identifying routes and individual scheduled trips
- connecting trips with ordered stops and scheduled arrival times
- matching static trips with GTFS-Realtime data
- comparing scheduled and actual arrival times for delay and punctuality analysis
- supporting future database design and historical analysis

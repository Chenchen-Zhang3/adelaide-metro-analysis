# Module Integration and Acceptance Checklist

## 1. Purpose

This checklist is used to review a module before it is integrated with other parts of the Adelaide Metro Real-Time Transport Analysis project.

The purpose is to make sure that each module works correctly, uses the agreed data structures and can connect with other modules without causing unnecessary integration problems.

## 2. General Module Check

Before a module is considered ready for integration, check that:

- The main function of the module has been completed.
- The module can run without critical errors.
- Required files are included in the repository.
- Required dependencies are documented.
- There are no unnecessary hard-coded local file paths.
- Important assumptions or limitations are documented.
- The module is understandable enough for another team member to review.

## 3. Shared GTFS Data Check

If the module uses GTFS or GTFS-Realtime data, check that:

- Shared GTFS field names are used where applicable.
- `stop_id` is used consistently.
- `route_id` is used consistently.
- `trip_id` is used consistently.
- `vehicle_id` is used consistently where required.
- Scheduled stop time information uses the agreed structure.
- Input data follows the agreed shared schemas where applicable.
- Output data can be used by the next module.
- Missing or optional data does not cause the whole module to fail.

The shared schemas are stored in:

```text
shared/schemas/
```

The current shared schemas include:

- `stop.schema.json`
- `route.schema.json`
- `trip.schema.json`
- `stop-time.schema.json`
- `trip-update.schema.json`
- `vehicle.schema.json`

## 4. Module Interface Check

Before integration, check that:

- The expected input of the module is clear.
- The expected output of the module is clear.
- Input and output formats match the agreed module interfaces.
- Shared field names are not changed unnecessarily.
- GTFS identifiers remain consistent between connected modules.
- Changes that affect another module have been communicated to the team.
- The module can work with the agreed sample data where applicable.

The agreed module interfaces are documented in:

```text
docs/architecture/module-interfaces.md
```

## 5. Data Processing Check

For modules that process GTFS or GTFS-Realtime data, check that:

- Required GTFS fields are read correctly.
- Stops, routes and trips remain correctly related.
- Stop times remain connected to the correct trips and stops.
- GTFS-Realtime records can be linked to the relevant route, trip or stop where the information is available.
- Invalid or incomplete data is handled appropriately.
- Data is not silently changed into an incompatible structure.

## 6. Testing Check

Before integration, check that:

- Relevant tests have been run.
- Sample data can be processed successfully.
- Invalid or missing data is handled where appropriate.
- Changes do not break existing validation.
- Any known testing limitations are documented.

For the Sprint 1 shared sample GTFS data, run:

```bash
python scripts/validate_fixtures.py
```

The expected result is that all sample datasets and cross-file GTFS references pass validation.

## 7. Database and Query Check

For database or query-related modules, check that:

- Processed GTFS data can be stored in the expected structure.
- Important GTFS identifiers are preserved.
- Stored records can be retrieved correctly.
- The database structure can support later historical analysis.
- Query results use a format that can be understood by the analysis or frontend modules.

These checks will be expanded as the database module develops in later sprints.

## 8. Analysis Check

For analysis-related modules, check that:

- The module uses the correct input data.
- Scheduled and real-time information are not mixed incorrectly.
- Delay calculations use the correct records.
- Results can be linked back to the relevant route, trip, stop or service.
- Missing data does not produce misleading results.
- The output can later be used by the frontend or visualisation module.

Detailed punctuality classifications and delay thresholds will be tested when the related analysis functions are implemented.

## 9. Frontend and Map Check

For map or frontend-related modules, check that:

- Stop and route information can be displayed using processed data.
- Geographic coordinates are read correctly.
- Missing records do not cause the entire interface to fail.
- Technical GTFS identifiers are not unnecessarily shown to the final user.
- Data received from backend or analysis modules uses an agreed format.
- Important information can be presented clearly to CASR researchers.

## 10. GitHub Check

Before a completed module is merged:

- Work has been completed on the correct feature branch.
- Changes have been committed.
- Changes have been pushed to GitHub.
- The feature branch contains the latest completed work.
- Relevant tests or validation have passed.
- A Pull Request is created when the work is ready for integration.
- Another team member reviews the changes where required.
- Any identified problems are corrected.
- Merge conflicts are resolved before merging into `main`.

## 11. Acceptance Checklist

A module can be considered ready for integration when the following items are satisfied:

- [ ] Main module function works.
- [ ] No critical errors remain.
- [ ] Required files are included.
- [ ] Dependencies are documented.
- [ ] Shared GTFS structures are followed where applicable.
- [ ] Input format is clear.
- [ ] Output format is clear.
- [ ] GTFS identifiers remain consistent.
- [ ] Sample or test data has been checked.
- [ ] Relevant validation or tests pass.
- [ ] Important assumptions or limitations are documented.
- [ ] Changes affecting other modules have been communicated.
- [ ] The correct GitHub feature branch has been used.
- [ ] Changes have been pushed to GitHub.
- [ ] The module is ready for team review.

## 12. Sprint 1 Use

During Sprint 1, this checklist will mainly be used to review the GTFS data processing, sample database, analysis and map-related modules before they are integrated.

At this stage, team members can develop their parts separately using the agreed shared GTFS structures and sample datasets.

When individual modules are completed, they will be reviewed against this checklist to identify data structure, interface or compatibility problems before merging them into `main`.

The checklist can be updated in later sprints when the team begins using real Adelaide Metro GTFS and GTFS-Realtime data and the modules become more closely integrated.
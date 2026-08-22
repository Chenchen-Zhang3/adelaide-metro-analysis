# Repository structure

This repository is organised by system responsibility rather than by team member.
Work on a feature branch and open a pull request before merging into `main`.

```text
backend/                 GTFS ingestion, transformation, storage and API work
  ingestion/             Source download and import jobs
  parsers/               Static GTFS parsers
  realtime/              GTFS-Realtime clients and protobuf decoding
  database/              Database models, migrations and repositories
  api/                   Backend endpoints
  services/              Business logic such as delay calculations
  tests/                 Backend-specific unit tests
frontend/                User interface and map visualisation
  components/            Reusable interface components
  pages/                 Application pages
  map/                   Map layers and map interactions
shared/                  Contracts used across the application
  schemas/               Shared data schemas and API payload definitions
  types/                 Shared types
  constants/             Shared constants and status values
docs/                    Project documentation
  architecture/          Architecture diagrams and decisions
  api/                   API endpoint documentation
  decisions/             Short records of agreed technical decisions
tests/                   Cross-feature and integration tests
scripts/                 Development and maintenance scripts
```

## Collaboration rules

- Use a feature branch for each Jira task, for example `feature/gtfs-static-parser`.
- Keep raw GTFS files and credentials out of Git unless the team explicitly agrees otherwise.
- Update shared schemas before relying on a new API field in another module.
- Link pull requests to their related Jira task where possible.

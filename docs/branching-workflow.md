# GitHub Branching and Merge Workflow

## 1. Purpose

This document explains how our team uses GitHub branches during development. The main purpose is to allow each team member to work on their own part of the project without directly changing the main branch.

## 2. Branch Structure

The `main` branch is used as the stable version of the project.

Each team member works on a separate feature branch based on their main responsibility.

Current branches include:

- `feature/system-integration`
- `feature/chenan-data-ingestion`
- `feature/lixuan-database`
- `feature/chengxi-analysis`
- `feature/pritish-map`

The feature branches are used for development and testing before changes are merged into `main`.

## 3. Basic Rules

1. Team members should not normally develop directly on `main`.
2. Each member should work on their own feature branch.
3. New branches should be created from the latest version of `main`.
4. Changes should be committed with a clear commit message.
5. Completed work should be pushed to GitHub.
6. Code should be checked before it is merged into `main`.

## 4. Starting Work

Before starting new work, update the local main branch:

```bash
git checkout main
git pull origin main
```

To create a new branch:

```bash
git checkout -b feature/example-module
```

To switch to an existing branch:

```bash
git checkout feature/example-module
```

## 5. Saving and Uploading Changes

Check the current changes:

```bash
git status
```

Add the changes:

```bash
git add .
```

Commit the changes:

```bash
git commit -m "Describe the completed change"
```

Push the changes to GitHub:

```bash
git push
```

For the first push of a new branch:

```bash
git push -u origin feature/example-module
```

## 6. Pull Request and Merge

When a task or module is ready:

1. Check that the code works correctly.
2. Run the relevant tests or validation.
3. Commit and push all changes to the feature branch.
4. Create a Pull Request from the feature branch to `main`.
5. Another team member reviews the changes.
6. Fix any problems or merge conflicts if required.
7. Merge the Pull Request after the review is complete.

## 7. Integration Checks

Before merging into `main`, we should check that:

- The module runs without critical errors.
- Relevant tests pass.
- Shared GTFS field names are used correctly.
- The module input and output are compatible with other parts of the project.
- Important changes are documented.
- Merge conflicts have been resolved.

For the Sprint 1 sample GTFS data, the validation script can be run using:

```bash
python scripts/validate_fixtures.py
```

The sample data should pass the validation before it is used for integration.

## 8. Shared Data Changes

Shared GTFS structures are stored in:

```text
shared/schemas/
```

If a team member needs to change a shared field or schema, the change should be discussed with the team first because other modules may depend on the same structure.

After changing a shared schema, the relevant sample data and validation should also be checked again.

## 9. Sprint 1 Workflow

During Sprint 1, each team member can develop their module separately using the agreed sample data and shared data structures.

When a module is ready, it will be checked for compatibility with the other modules before being merged into `main`.

This helps the team develop different parts of the system at the same time while reducing integration problems later.
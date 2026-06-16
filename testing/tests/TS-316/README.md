# TS-316

Validates that JQL Search keeps pagination deterministic by using issue key
ascending as the default sort and as the final tie-breaker when an explicit
priority sort is present.

The automation:
1. launches the real `TrackStateApp` with a ticket-scoped repository whose issue
   list is intentionally unsorted
2. opens `JQL Search` and submits `project = TRACK`
3. verifies the first six visible results are sorted by issue key ascending,
   then appends the second page and confirms the full list stays stable
4. submits `project = TRACK ORDER BY priority DESC`
5. verifies equal-priority issues still sort by key ascending, including a
   medium-priority tie that crosses the visible page boundary

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-316/test_ts_316.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: JQL Search shows default results in key ascending order, keeps
same-priority rows in key ascending order under ORDER BY priority DESC, and
appends the next page without duplicate, skipped, or reordered issues.

Fail: Default ordering is not by key, equal-priority rows are not key-sorted,
or loading the next page changes the existing order or boundary.
```

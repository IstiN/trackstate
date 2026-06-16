# TS-137

Validates that a repository-service delete request for a non-existent issue key
returns the exact not-found error and does not create tombstone artifacts or
deleted-key metadata.

The automation covers the ticket from the repository-service consumer
perspective against a temporary local Git-backed TrackState repository:
1. seed a clean repository with active issue `TRACK-122`
2. attempt to delete `MISSING-999` through `LocalTrackStateRepository.deleteIssue`
3. verify the exact error message, confirm
   `TRACK/.trackstate/tombstones/` and
   `TRACK/.trackstate/index/tombstones.json` are still absent, and confirm the
   surviving issue remains searchable and unchanged

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-137/test_ts_137.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```

# TS-153

Validates that archiving a non-existent issue key returns a clear repository
not-found error instead of a low-level interface failure.

The automation covers the ticket from the repository-service consumer
perspective against a temporary local Git-backed TrackState repository:
1. seed a clean repository with active issue `TRACK-122`
2. attempt to archive `MISSING-999` through `LocalTrackStateRepository.archiveIssue`
3. verify the exact repository error, confirm no `NoSuchMethodError` surfaces,
   and confirm the surviving issue plus Git worktree remain unchanged

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-153/test_ts_153.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```

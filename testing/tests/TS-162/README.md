# TS-162

Validates that updating a non-existent issue key returns a clear repository
not-found error instead of leaking the low-level Git provider failure.

The repository contract exposes dedicated update methods rather than a single
`updateIssue` entry point, so this automation covers the consumer-visible issue
edit path through `LocalTrackStateRepository.updateIssueDescription`.

The automation covers the ticket from the repository-service consumer
perspective against a temporary local Git-backed TrackState repository:
1. seed a clean repository with active issue `TRACK-122`
2. attempt to update `MISSING-888` through
   `LocalTrackStateRepository.updateIssueDescription`
3. verify the exact repository error and confirm the surviving issue plus Git
   worktree remain unchanged

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-162/test_ts_162.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```

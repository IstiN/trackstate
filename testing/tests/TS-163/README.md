# TS-163

Validates that archiving an existing issue does not leak low-level Git provider
failures to repository-service consumers.

The automation covers the ticket from the repository-service consumer
perspective against a temporary local Git-backed TrackState repository:
1. seed a clean repository with active issue `TRACK-122`
2. force the archive commit to fail with a generic Git/provider error
3. invoke `LocalTrackStateRepository.archiveIssue` for `TRACK-122`
4. verify the caller receives a `TrackStateRepositoryException` without
   provider/Git implementation details and confirm repository search still
   shows the issue as active from `HEAD`

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-163/test_ts_163.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture and
injects a custom Git process runner, so no external credentials or environment
variables are required.

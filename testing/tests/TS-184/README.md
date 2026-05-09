# TS-184

Validates the normal archive success path for an existing issue through the live
`LocalTrackStateRepository.archiveIssue` implementation.

The automation covers the ticket from the repository-service consumer
perspective against a temporary local Git-backed TrackState repository:
1. seed a clean repository with active issue `TRACK-122`
2. invoke `LocalTrackStateRepository.archiveIssue` for `TRACK-122`
3. verify the operation completes without throwing and returns `TRACK-122`
   marked as archived
4. verify the active artifact `TRACK/TRACK-122/main.md` is removed and the
   reloaded repository state marks the issue as archived
5. verify repository search still finds `TRACK-122` and reports it as archived

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-184/test_ts_184.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

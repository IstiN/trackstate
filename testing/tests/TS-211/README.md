# TS-211

Validates that archiving an existing issue updates the repository index and
same-session path resolution to the archived storage path instead of the former
active-storage path.

The automation covers the ticket from the repository-service consumer
perspective against a temporary local Git-backed TrackState repository:
1. seed a clean repository with active issue `TRACK-122`
2. resolve `TRACK-122` before archiving and confirm it points to
   `TRACK/TRACK-122/main.md`
3. invoke `LocalTrackStateRepository.archiveIssue` for `TRACK-122`
4. resolve and search for `TRACK-122` again through the same repository-facing
   services
5. verify both the repository index and surfaced issue metadata now point to
   `TRACK/.trackstate/archive/TRACK-122/main.md`

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-211/test_ts_211.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected output when the test passes

```text
00:00 +1: All tests passed!
```

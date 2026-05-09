# TS-174

Validates that archiving an existing issue succeeds, moves the issue artifact
out of active storage, and exposes the archived lifecycle state through the
same repository surfaces that integrated clients use.

The automation covers the ticket from the repository-service consumer
perspective against a temporary local Git-backed TrackState repository:
1. seed a clean repository with active issue `TRACK-122`
2. invoke `LocalTrackStateRepository.archiveIssue` for `TRACK-122`
3. verify the active-storage artifact `TRACK/TRACK-122/main.md` is removed and
   the repository no longer resolves `TRACK-122` to the active path
4. verify the returned issue, repository index, and committed repository state
   all mark the issue as archived
5. verify a standard repository search still finds `TRACK-122` and reports it
   as archived

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-174/test_ts_174.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected output when the test passes

```text
00:00 +1: All tests passed!
```

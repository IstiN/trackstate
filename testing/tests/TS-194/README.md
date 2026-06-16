# TS-194

Validates that deleting `TRACK-122` physically removes the entire issue storage
directory, not just the tracked files inside it.

The automation covers the ticket in two layers against the same temporary local
Git-backed repository fixture:
1. delete `TRACK-122` through the repository service, verify tombstone metadata,
   confirm `TRACK/TRACK-122/main.md` and `TRACK/TRACK-122/attachment.txt` are
   gone, and assert the `TRACK/TRACK-122/` directory itself no longer exists
2. launch the real `TrackStateApp`, open *JQL Search*, and verify `TRACK-122`
   disappears from visible results while `TRACK-123` remains visible

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-194/test_ts_194.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected passing output

```text
00:00 +2: All tests passed!
```

# TS-173

Validates that deleting `TRACK-777` still succeeds when the legacy
`.trackstate/index/deleted.json` file does not exist before the delete starts.

The automation covers the ticket in two layers against the same temporary local
Git repository fixture:
1. delete `TRACK-777` through the repository service, verify
   `.trackstate/tombstones/TRACK-777.json` and
   `.trackstate/index/tombstones.json`, and confirm the legacy
   `.trackstate/index/deleted.json` file remains absent throughout the workflow
2. launch the real `TrackStateApp`, open *JQL Search*, and verify the deleted
   issue is no longer shown while the surviving issue remains visible

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-173/test_ts_173.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected passing output

```text
00:00 +2: All tests passed!
```

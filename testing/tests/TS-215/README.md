# TS-215

Validates that deleting multiple issues concurrently keeps the legacy
`.trackstate/index/deleted.json` file present and unchanged while creating all
expected tombstone artifacts.

The automation covers the ticket against a temporary local Git-backed TrackState
repository:
1. seeds a clean repository with three active delete targets, one surviving
   issue, and a legacy `.trackstate/index/deleted.json` file
2. verifies the legacy deleted index and active issue search results before the
   concurrent delete workflow begins
3. invokes concurrent `deleteIssue` calls for `TRACK-721`, `TRACK-722`, and
   `TRACK-723` through the repository service
4. verifies each tombstone file plus `.trackstate/index/tombstones.json`
5. verifies the legacy deleted index file remains byte-for-byte unchanged
6. verifies integrated repository search shows only the surviving issue after
   the concurrent workflow completes

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-215/test_ts_215.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```

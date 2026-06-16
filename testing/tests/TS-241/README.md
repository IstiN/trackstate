# TS-241: Delete multiple issues concurrently — shared tombstone index records all deletions

Validates that concurrent delete operations preserve every deleted issue in
`.trackstate/index/tombstones.json` instead of losing entries from overlapping
write cycles.

The automation covers the ticket against a temporary local Git-backed TrackState
repository:
1. seeds three active delete targets and one surviving issue
2. verifies search shows all active issues before deletion
3. invokes concurrent `deleteIssue` calls through the repository service
4. inspects `.trackstate/index/tombstones.json` to confirm all deleted keys are
   present
5. verifies user-visible search behavior after reload shows only the surviving
   issue

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-241/test_ts_241.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected passing output

```text
00:00 +1: All tests passed!
```

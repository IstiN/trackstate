# TS-282

Validates that re-parenting `TASK-1` from `EPIC-1` to `EPIC-2` performs a
physical directory move that Git reports as a rename while preserving the issue
key and updating the repository index to the new canonical path.

The automation covers the ticket from the shared testing-component layer against
a temporary local Git-backed TrackState repository:
1. seed a clean repository where `TASK-1` starts under `REPARENT/EPIC-1/TASK-1/`
2. invoke the production `reassignIssue` mutation with `parentKey: "EPIC-2"`
3. verify the typed success result preserves `TASK-1` and exposes the new
   storage path
4. inspect the filesystem, latest Git commit, and rebuilt
   `.trackstate/index/issues.json` metadata to confirm the move to
   `REPARENT/EPIC-2/TASK-1/`
5. reload the repository and confirm the moved issue remains discoverable in
   the app with the same key, summary, description, and acceptance criterion

## Install dependencies

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter pub get
```

## Run this test

```bash
/opt/hostedtoolcache/flutter/stable-3.35.3-x64/flutter/bin/flutter test testing/tests/TS-282/test_ts_282.dart -r expanded
```

## Required configuration

This test creates its own temporary local Git-backed repository fixture, so no
external credentials or environment variables are required.

## Expected output when the test passes

```text
00:00 +1: All tests passed!
```

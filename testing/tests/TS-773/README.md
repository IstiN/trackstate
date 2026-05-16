# TS-773

Reworks the TS-773 automation so it no longer treats the existing
`hostedRepository + empty changedPaths` fallback as proof of an explicit
`load_snapshot_delta=1` contract.

The test now:

1. launches the real `TrackStateApp`
2. opens **JQL Search**, submits `status = Open`, and selects `TRACK-773-B`
3. runs a control hosted sync **without** an explicit flag and checks whether
   the app still defaults to a full snapshot reload
4. runs a second hosted sync where the fixture requests `load_snapshot_delta=1`
   but can only expose the current production `RepositorySyncCheck` boundary
5. compares both payloads and fails on the real product gap when they are not
   distinguishable and/or the control path still reloads globally

## Run this test

```bash
flutter test testing/tests/TS-773/test_ts_773.dart --reporter expanded
```

## Required configuration

No external credentials are required. The test uses an in-memory repository
fixture inside `testing/tests/TS-773/support/`.

# TS-773

Automates the fixed TS-773 sync contract where a hosted snapshot reload only
occurs when the explicit `load_snapshot_delta=1` request reaches the production
boundary as a dedicated hosted reload signal.

The test now:

1. launches the real `TrackStateApp`
2. opens **JQL Search**, submits `status = Open`, and selects `TRACK-773-B`
3. runs a control hosted sync **without** an explicit flag and verifies the app
   does **not** default to a full snapshot reload
4. runs a second hosted sync where the fixture requests `load_snapshot_delta=1`
   and verifies the production sync contract exposes a dedicated explicit reload
   signal
5. compares both payloads, the `loadSnapshot` deltas, and the visible Issue-B
   detail state

## Run this test

```bash
flutter test testing/tests/TS-773/test_ts_773.dart --reporter expanded
```

## Required configuration

No external credentials are required. The test uses an in-memory repository
fixture inside `testing/tests/TS-773/support/`.

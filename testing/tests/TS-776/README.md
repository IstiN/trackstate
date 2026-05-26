# TS-776

Validates that a hosted sync payload which omits the
`load_snapshot_delta` signal does not default to a full snapshot reload.

The automation:
1. launches the real `TrackStateApp` with the hosted sync repository fixture
   reused from `TS-773`
2. opens **JQL Search**, submits `status = Open`, and selects `TRACK-773-B`
3. verifies the initial Issue-B detail text before the sync
4. runs a hosted background sync whose exposed `signals` map omits
   `load_snapshot_delta`
5. checks that `loadSnapshot` is not called, the `load_snapshot_delta` counter
   stays at `0`, and the visible Issue-B detail remains unchanged

## Run this test

```bash
flutter test testing/tests/TS-776/test_ts_776.dart --reporter expanded
```

## Required configuration

No external credentials are required. The test uses the in-memory hosted sync
fixture from `testing/tests/TS-773/support/`.

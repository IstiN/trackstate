# TS-773

Automates the workspace sync scenario where a background event explicitly
requests a global snapshot reload through `load_snapshot_delta=1`.

The test covers the production widget flow end to end:

1. launch the real `TrackStateApp`
2. open **JQL Search**, submit `status = Open`, and select `TRACK-773-B`
3. queue a background sync event that represents explicit `load_snapshot_delta=1`
4. trigger the production app-resume workspace sync path
5. verify the selected issue detail refreshes from a full snapshot reload and
   `load_snapshot_delta` increments to `1`

## Run this test

```bash
flutter test testing/tests/TS-773/test_ts_773.dart --reporter expanded
```

## Required configuration

No external credentials are required. The test uses an in-memory repository
fixture inside `testing/tests/TS-773/support/`.

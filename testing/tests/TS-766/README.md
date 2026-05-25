# TS-766

Validates that an attachments-only hosted workspace sync does not increment the
global `load_snapshot_delta` counter and hydrates only the selected issue's
attachments surface through the production TrackState app.

The test uses an isolated mutable hosted repository fixture so the real sync
orchestration path, repository refresh dispatcher, and visible Issue-C
Attachments tab are exercised end-to-end.

## Run this test

```bash
flutter test testing/tests/TS-766/test_ts_766.dart --reporter expanded
```

## Expected result

```text
Pass: an attachments-only sync updates the visible Issue-C attachment row,
dispatches only an attachments hydration for Issue-C, and keeps
load_snapshot_delta unchanged.

Fail: the attachments-only sync is ignored, triggers non-attachment hydration
scopes, fails to update the visible attachment row, or increments the hosted
snapshot reload counter.
```

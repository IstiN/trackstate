# TS-740

Validates that a comments-only hosted workspace sync does not increment the
global `load_snapshot_delta` counter while the visible Issue-C comments surface
still refreshes through the production TrackState app.

The test reuses the proven TS-734 hosted refresh fixture so the scenario runs
through the real sync orchestration path, repository refresh dispatcher, and
visible issue detail UI.

## Run this test

```bash
flutter test testing/tests/TS-740/test_ts_740.dart --reporter expanded
```

## Expected result

```text
Pass: a comments-only sync updates the visible Issue-C comment content through
the refresh dispatcher and leaves load_snapshot_delta unchanged.

Fail: the comments-only sync is not processed, updates the wrong hydration
scope, or increments the hosted snapshot reload counter.
```

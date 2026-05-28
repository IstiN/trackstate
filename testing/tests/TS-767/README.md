# TS-767

Validates that a comments-only hosted background sync for Issue-C stays scoped to
the comments domain and does not escalate into issue-level non-comments
hydration or a project metadata reload path.

The test reuses the proven TS-734 mutable hosted repository fixture so the
scenario runs through the real TrackState workspace sync orchestration, visible
Issue Detail UI, and hosted refresh dispatcher.

## Run this test

```bash
flutter test testing/tests/TS-767/test_ts_767.dart --reporter expanded
```

## Expected result

```text
Pass: a comments-only sync updates the visible Issue-C comment, dispatches only
comments hydration for Issue-C, and leaves load_snapshot_delta unchanged.

Fail: the event triggers non-comments issue hydration, causes a snapshot reload,
or does not refresh the visible Comments tab correctly.
```

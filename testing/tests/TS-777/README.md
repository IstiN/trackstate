# TS-777

Validates that an explicit `load_snapshot_delta=0` hosted sync request bypasses
the global snapshot reload path.

The test drives the production Flutter app, opens **JQL Search**, selects
`TRACK-777-B`, queues a hosted background sync that internally requests
`load_snapshot_delta=0`, and verifies both:

1. orchestration behavior (`loadSnapshot` delta stays `0`), and
2. the user-facing result (the visible issue detail remains unchanged)

## Run this test

```bash
flutter test testing/tests/TS-777/test_ts_777.dart --reporter expanded
```

## Expected result

```text
Pass: the explicit false hosted sync is processed, no global snapshot reload
occurs, and the visible Issue-B detail stays on the original text.

Fail: the explicit false hosted sync still triggers loadSnapshot and/or replaces
the visible Issue-B detail with the queued synced text.
```

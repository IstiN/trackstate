# TS-777

Validates that an explicit `load_snapshot_delta=0` hosted sync request is
distinguishable from the unflagged hosted sync path while still bypassing the
global snapshot reload.

The test drives the production Flutter app, opens **JQL Search**, selects
`TRACK-777-B`, runs both an unflagged hosted sync and an explicit
`load_snapshot_delta=0` hosted sync attempt, and verifies both:

1. orchestration behavior (`loadSnapshot` delta stays `0` for both paths),
2. the user-facing result (the visible issue detail remains unchanged), and
3. the public `RepositorySyncCheck` payloads are different enough for the app
   to distinguish explicit false from omission.

## Run this test

```bash
flutter test testing/tests/TS-777/test_ts_777.dart --reporter expanded
```

## Expected result

```text
Pass: the explicit false hosted sync is publicly distinguishable from the
unflagged hosted sync, no global snapshot reload occurs, and the visible
Issue-B detail stays on the original text.

Fail: either hosted sync triggers `loadSnapshot`, the visible Issue-B detail is
replaced, or the explicit false request still collapses into the same public
payload as the unflagged hosted sync.
```

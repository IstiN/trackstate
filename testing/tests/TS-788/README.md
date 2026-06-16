# TS-788

Validates that hosted background sync changed paths which only *partially*
match an allow-listed domain keyword are still treated as malformed and ignored.

The test drives the production Flutter app with a mutable
`ProviderBackedTrackStateRepository`, opens Issue-C on the visible Comments tab,
publishes malformed changed paths (`TRACK-741C/comments_and_more` and
`comments/TRACK-741C`), and then checks both:

1. orchestration behavior (`hydrateIssue` delta and `load_snapshot_delta`), and
2. the user-facing result (the original visible comment remains unchanged)

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-788/test_ts_788.dart --reporter expanded
```

## Expected result

```text
Pass: malformed changed paths that only partially match the comments allow-list
are filtered out, no snapshot reload occurs, and the visible Issue-C comment
stays unchanged.

Fail: the malformed path still triggers visible hydration and/or increments
load_snapshot_delta instead of being ignored.
```

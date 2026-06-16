# TS-787

Validates that a hosted background sync event with an empty-string domain path is
ignored by the workspace-sync filtering logic instead of dispatching refreshes
or falling back to a global snapshot reload.

The test drives the production Flutter app with a mutable
`ProviderBackedTrackStateRepository`, opens Issue-C on the visible Comments tab,
publishes an empty changed path, and then checks both:

1. orchestration behavior (`hydrateIssue` delta and `loadSnapshot` delta), and
2. the user-facing result (the original visible comment remains unchanged)

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-787/test_ts_787.dart --reporter expanded
```

## Expected result

```text
Pass: the empty hosted sync path is filtered out, no snapshot reload occurs,
and the visible Comments tab keeps the original Issue-C comment.

Fail: the empty path causes a snapshot reload and/or rehydrates visible issue
content instead of being ignored.
```

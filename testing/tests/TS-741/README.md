# TS-741

Validates that a hosted background sync event with an undefined or unknown
domain scope is ignored by the workspace-sync domain filter instead of falling
back to a global snapshot reload.

The test drives the production Flutter app with a mutable
`ProviderBackedTrackStateRepository`, opens Issue-C on the visible Comments tab,
publishes an unknown changed path, and then checks both:

1. orchestration behavior (`hydrateIssue` delta and `loadSnapshot` delta), and
2. the user-facing result (the original visible comment remains unchanged)

## Run this test

```bash
flutter test testing/tests/TS-741/test_ts_741.dart --reporter expanded
```

## Expected result

```text
Pass: the unknown hosted sync scope is filtered out, no snapshot reload occurs,
and the visible Comments tab keeps the original Issue-C comment.

Fail: the unknown scope causes a snapshot reload and/or rehydrates visible issue
content instead of being ignored.
```

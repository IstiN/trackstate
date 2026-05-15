# TS-756

Validates that a hosted background sync event containing both a valid comments
path and an unknown metadata path only processes the allow-listed comments
domain.

The test drives the production Flutter app with a mutable
`ProviderBackedTrackStateRepository`, opens Issue-C on the visible Comments tab,
publishes one valid comments change plus one unknown path, and then checks both:

1. orchestration behavior (`hydrateIssue` delta and `loadSnapshot` delta), and
2. the user-facing result (the visible comment updates in place, while the
   unknown path is ignored).

## Run this test

```bash
flutter test testing/tests/TS-756/test_ts_756.dart --reporter expanded
```

## Expected result

```text
Pass: the valid comments change is hydrated, the unknown path is ignored, no
snapshot reload occurs, and the visible Comments tab shows the updated Issue-C
comment.

Fail: the unknown path triggers extra refresh behavior and/or a snapshot reload,
or the valid comments change does not appear in the visible Comments tab.
```

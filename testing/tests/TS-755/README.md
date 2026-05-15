# TS-755

Validates that a hosted background sync event with an undefined or unknown
domain scope does not dispatch issue-level hydration for TRACK-741C and does
not replace the visible comment content in the open Comments tab.

The test drives the production Flutter app with the existing mutable hosted
repository fixture from TS-741, opens Issue-C on the visible Comments tab,
publishes an unknown changed path, and then checks both:

1. orchestration behavior (`hydration_delta_count` stays `0`), and
2. the user-facing result (the original visible comment remains unchanged)

## Run this test

```bash
flutter test testing/tests/TS-755/test_ts_755.dart --reporter expanded
```

## Expected result

```text
Pass: the unknown hosted sync scope is filtered at the issue level, no
hydration calls are dispatched for TRACK-741C, and the visible Comments tab
keeps the original Issue-C comment.

Fail: the unknown scope dispatches issue hydration and/or replaces visible
Issue-C comment content instead of being ignored.
```

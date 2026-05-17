# TS-811

Automates the JQL Search regression where a background sync reorders results by
priority and the selected issue must stay attached to its stable ID instead of
the old list index.

The test covers the production widget flow end to end:

1. launch the real `TrackStateApp`
2. open **JQL Search**, run `project = TRACK AND status != Done ORDER BY priority DESC`, and select `TRACK-811-A`
3. apply a background sync update that promotes `TRACK-811-B` from Medium to Highest so it moves above the selected row
4. trigger the production app-resume workspace sync refresh path
5. verify `TRACK-811-A` remains visibly selected at its new list position and its detail panel stays open

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-811/test_ts_811.dart --reporter expanded
```

## Environment

- Flutter widget test runtime
- Production search/detail widget tree
- Mutable in-memory workspace sync repository fixture

## Expected result

After the sync refresh reorders the list, the app should keep the selection on
`TRACK-811-A`, move that row to its new position under `TRACK-811-B`, and keep
the `TRACK-811-A` detail panel open.

# TS-752

Validates that the production unavailable banner shown after a background sync
removes the currently selected JQL Search issue stays non-blocking.

The automation:
1. opens **JQL Search** with `TRACK-12` selected while `TRACK-11` remains visible
   in the results list
2. emits a hosted sync update that removes `TRACK-12` from the workspace data
3. waits for the production refresh state to settle and for the
   `no longer available` banner to appear
4. clicks the remaining `TRACK-11` result while the banner is still visible
5. verifies `TRACK-11` becomes selected and its detail panel loads normally

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-752/test_ts_752.dart --reporter expanded
```

## Environment

- Flutter widget test runtime
- Production search/detail widget tree
- Hosted provider-backed mutable repository fixture

## Expected result

After the sync refresh removes the selected issue, the app should show the
unavailable banner without intercepting the result list so the user can still
open the remaining issue and load its details.

# TS-753

Validates that the production issue-unavailable notification banner shown after a
background sync removes the selected issue is manually dismissible.

The automation:
1. opens **JQL Search** with `TRACK-12` selected in the Search and Detail
   surface
2. emits a hosted sync update that removes `TRACK-12` from
   `.trackstate/index/issues.json` and the repository tree
3. waits for the production "no longer available" banner to appear
4. dismisses the banner through the visible UI and confirms it is removed

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-753/test_ts_753.dart --reporter expanded
```

## Environment

- Flutter widget test runtime
- Production search/detail widget tree
- Hosted provider-backed mutable repository fixture

## Expected result

After the sync refresh removes the selected issue, the app should show the
non-blocking unavailable notification and let the user dismiss it so the banner
is removed from the screen.

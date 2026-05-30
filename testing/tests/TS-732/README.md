# TS-732

Validates the production JQL Search fallback behavior when a background sync
removes the currently selected issue from the workspace index and repository
tree.

The automation:
1. opens **JQL Search** with `TRACK-12` selected in the Search and Detail
   surface
2. emits a hosted sync update that removes `TRACK-12` from
   `.trackstate/index/issues.json` and the repository tree
3. observes the refreshed search/detail surface for the ticket's required
   fallback behavior

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-732/test_ts_732.dart --reporter expanded
```

## Environment

- Flutter widget test runtime
- Production search/detail widget tree
- Hosted provider-backed mutable repository fixture

## Expected result

After the sync refresh removes the selected issue, the app should clear the
invalid detail selection, keep the user in the current **JQL Search** section,
and show a non-blocking message explaining that the previous issue is no longer
available.

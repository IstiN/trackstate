# TS-903

Validates that a background hosted sync which updates the currently selected
issue keeps the same issue selected in **JQL Search**, refreshes the visible
detail content, and does not show the "issue no longer available" banner.

The automation:
1. opens **JQL Search** with `TRACK-12` selected in the Search and Detail
   surface
2. emits a hosted sync update that keeps `TRACK-12` in the repository index
   while changing its summary and description
3. observes the refreshed search/detail surface for the ticket's required
   preserved-selection behavior

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-903/test_ts_903.dart --reporter expanded
```

## Environment

- Flutter widget test runtime
- Production search/detail widget tree
- Hosted provider-backed mutable repository fixture

## Expected result

After the sync refresh updates the selected issue, the same issue should remain
selected with the highlight still visible, the detail surface should show the
updated information, and no "issue no longer available" notification should
appear.

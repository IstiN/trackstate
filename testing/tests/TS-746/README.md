# TS-746

Automates the JQL Search regression where a workspace sync refresh reorders the
results list after the selected issue changes a sort-relevant field.

The test covers the production widget flow end to end:

1. launch the real `TrackStateApp`
2. open **JQL Search**, submit `status = Open ORDER BY priority DESC`, and
   select `TRACK-746-B`
3. apply a background sync update that demotes the selected issue so the active
   query reorders the visible rows
4. trigger the production app-resume workspace sync refresh path
5. verify the same issue stays visibly selected at its new index while the
   detail panel remains open and shows the refreshed description

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-746/test_ts_746.dart --reporter expanded
```

## Required configuration

No external credentials are required. The test uses an in-memory repository
fixture inside `testing/tests/TS-746/support/`.

## Expected result

```text
Pass: the selected issue moves to its reordered JQL Search position after the
sync refresh, keeps its visible selected/highlight state, and remains open in
the detail panel with refreshed data.

Fail: the active query is lost, the rows do not reorder as expected, the
selection highlight moves to a different issue or disappears, or the detail
panel closes or does not show the refreshed content for TRACK-746-B.
```

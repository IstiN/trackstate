# TS-751

Validates that a manual JQL Search submission auto-selects the first visible
result after the linked TS-749 sync-refresh fix clears a removed selection.

The automation:
1. opens the production **JQL Search** surface with `TRACK-751-A` selected
2. triggers the hosted workspace-sync fixture to remove `TRACK-751-A` and waits
   for the selection-cleared unavailable notice state
3. enters `priority = High ORDER BY key ASC` into the visible JQL field
4. manually submits the JQL field
5. verifies `TRACK-751-B` becomes the highlighted selection while
   `TRACK-751-C` stays visible but unselected
6. verifies the detail panel renders the selected issue details for
   `TRACK-751-B`

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-751/test_ts_751.dart --reporter expanded
```

## Required environment / config

- Flutter SDK available on `PATH`
- Flutter widget test runtime
- Production search/detail widget tree
- Hosted provider-backed mutable repository fixture that simulates the
  TS-749 sync-removal refresh before the manual search

## Expected pass / fail behavior

- **Pass:** after the sync-cleared state, manually submitting
  `priority = High ORDER BY key ASC` selects and highlights `TRACK-751-B`,
  keeps `TRACK-751-C` visible but unselected, and renders `TRACK-751-B`
  details in the detail panel.
- **Fail:** the manual submission does not select the first visible result,
  highlights the wrong row, hides the expected result rows, or renders the
  wrong issue details after submission.

# TS-317

Validates that the JQL Search screen appends paginated results with the visible
`Load more` control and keeps the user's active query/sort state intact.

The automation:
1. launches the real `TrackStateApp` with a ticket-scoped paginated repository
2. opens `JQL Search` and submits a query that returns two pages of issues
3. confirms the first page shows six ordered issue rows plus a visible
   `Showing 6 of 12 issues` summary and `Load more` control
4. activates `Load more` from the user-facing search panel
5. verifies the next six results are appended in order, the query text remains
   unchanged, and the last page hides the `Load more` control

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-317/test_ts_317.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: JQL Search shows the first page of ordered issues, appends the next page
without replacing or reordering the existing results, keeps the submitted query
visible in the search field, and removes the Load more control on the last page.

Fail: Load more is missing before the last page, tapping it replaces/reorders
existing results, the query text changes unexpectedly, or the final page still
shows a Load more control.
```

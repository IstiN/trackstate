# TS-318

Validates the JQL Search accessibility contract for the production-visible
search surface with paginated results.

The automation:
1. opens the JQL Search screen with Semantics enabled
2. verifies visible pagination content, including `Showing 6 of 8 issues`,
   `Paged issue 1`, `Paged issue 6`, and `Load more`
3. checks that the Search input and `Load more` control expose unique,
   meaningful semantics labels
4. exercises Tab and Shift+Tab traversal across the input, visible result rows,
   and pagination control
5. measures the rendered `Load more` styling and contrast against the AC5
   `primary` and `primarySoft` token expectations

## Run this test

```bash
flutter test testing/tests/TS-318/test_ts_318.dart -r expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test uses the local widget fixture provided by this repository

## Expected result

```text
Pass: the JQL Search screen exposes unique Search and Load more semantics
labels, keeps keyboard traversal in a logical order from the search input
through the visible paginated results to the pagination control, and renders
the Load more button with WCAG AA contrast and the expected AC5 primary and
primarySoft tokens.

Fail: the Search input semantics are merged or duplicated, keyboard focus does
not advance through the visible result rows and Load more control, or the Load
more button styling diverges from the expected AC5 tokens even if contrast
still passes.
```

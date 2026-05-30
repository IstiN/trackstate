# TS-331

Validates the collaboration tab strip accessibility contract on the production-visible
issue detail surface.

The automation:
1. opens issue detail with Semantics enabled through the shared accessibility fixture
2. verifies the visible collaboration tab labels `Detail`, `Comments`,
   `Attachments`, and `History`
3. checks the collaboration semantics tree exposes exactly one focusable button
   target per tab
4. tabs forward through the issue detail and confirms keyboard focus reaches the
   collaboration strip in the expected `Detail -> Comments -> Attachments ->
   History` order

## Run this test

```bash
flutter test testing/tests/TS-331/test_ts_331.dart -r expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test uses the local widget fixture provided by this repository

## Expected result

```text
Pass: issue detail shows the four collaboration tabs as visible text, exposes
exactly one keyboard-focusable semantics node for each tab, and keyboard Tab
navigation reaches the strip in logical order from Detail through History.

Fail: Detail is missing from the focus sequence, any collaboration tab is
duplicated as a separate focus stop, or keyboard traversal reaches the tab strip
in the wrong order.
```

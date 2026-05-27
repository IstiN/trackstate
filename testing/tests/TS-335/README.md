# TS-335

Validates that the production-visible **Create issue** form opens as a true
full-screen surface on a `390x844` mobile viewport.

The automation:
1. sets the widget runtime viewport to `390x844`
2. opens the real Create issue surface from the running app shell
3. confirms the visible heading, key fields, and actions a user relies on
4. measures the rendered surface bounds and verifies it fills the viewport from
   origin `(0, 0)` without side or bottom insets
5. drains Flutter framework exceptions to catch layout regressions a user would
   experience while opening the form

## Run this test

```bash
flutter test testing/tests/TS-335/test_ts_335.dart
```

## Expected result

```text
Pass: the Create issue form opens on a 390x844 viewport as a full-screen mobile
surface at origin (0,0) with no side or bottom insets, and the user-visible
form content remains rendered without framework exceptions.

Fail: the form opens inset, leaves any side/bottom gap, loses expected visible
copy, or opening the form surfaces a framework/layout exception.
```

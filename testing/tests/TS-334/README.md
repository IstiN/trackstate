# TS-334

Validates that the production-visible **Create issue** desktop surface stays
flush with the right viewport edge on a `1440x960` desktop viewport.

The automation:
1. opens the real Create issue surface from the widget runtime
2. confirms the visible title, key fields, and actions a user relies on
3. verifies the rendered surface remains a right-docked side sheet
4. asserts the rendered right edge is flush with the viewport, preventing the
   previous large right inset regression

## Run this test

```bash
flutter test testing/tests/TS-334/test_ts_334.dart
```

## Expected result

```text
Pass: the Create issue desktop surface stays right-docked and its right edge is
flush with the 1440px viewport.

Fail: the Create issue form loses visible user-facing content, stops rendering
as a side sheet, or leaves a non-zero right inset instead of docking to the
viewport edge.
```

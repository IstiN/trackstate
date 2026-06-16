# TS-337

Validates the production-visible **Create issue** desktop layout against a
right-docked golden baseline.

The automation:
1. opens the real Create issue surface from the running app shell
2. confirms the visible heading, primary fields, and actions a user relies on
3. verifies the rendered surface is docked to the right edge on a `1440x960`
   viewport
4. captures the rendered desktop viewport and compares it pixel-for-pixel with
   the approved golden baseline

## Run this test

```bash
flutter test testing/tests/TS-337/test_ts_337.dart
```

## Expected result

```text
Pass: the Create issue desktop surface stays right-docked and the rendered
viewport matches the stored golden baseline.

Fail: the Create issue form is missing visible user-facing content, no longer
reaches the right edge, or the rendered desktop viewport regresses from the
stored golden baseline.
```

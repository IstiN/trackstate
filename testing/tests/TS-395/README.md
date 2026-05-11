# TS-395

Validates that the production-visible **Create issue** form opens directly in a
`1440x640` desktop viewport with vertical scrolling already active on the first
render.

The automation:
1. launches the real Create issue flow with the viewport preset to `1440x640`
2. verifies the visible form renders key user-facing labels without any
   Flutter/RenderFlex overflow exception during the initial build
3. confirms the Create issue body exposes vertical scrolling immediately on load
4. scrolls to the bottom and verifies the visible **Save** and **Cancel**
   actions remain reachable to the user

## Run this test

```bash
flutter test testing/tests/TS-395/test_ts_395.dart
```

## Expected result

```text
Pass: The Create issue form opens at 1440x640 without RenderFlex overflow,
vertical scrolling is already available on the initial build, and the bottom
Save and Cancel actions are reachable after scrolling.

Fail: Opening the form at 1440x640 throws a framework exception, vertical
scrolling is not initialized on load, or the bottom actions cannot be reached.
```

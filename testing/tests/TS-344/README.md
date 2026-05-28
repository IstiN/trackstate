# TS-344

Validates that the production-visible **Create issue** form remains usable when
the desktop viewport height is reduced and the form body must scroll vertically.

The automation:
1. opens the real Create issue form at `1440x960`
2. reduces only the viewport height in stages down to `400px`
3. verifies the visible form keeps rendering key user-facing content without
   Flutter/RenderFlex overflow exceptions
4. confirms the Create issue body exposes vertical scroll overflow at the
   shortest height
5. scrolls to the bottom and verifies the visible **Save** and **Cancel**
   actions remain reachable to the user

## Run this test

```bash
flutter test testing/tests/TS-344/test_ts_344.dart
```

## Expected result

```text
Pass: the Create issue form keeps its key fields visible during the height
transition, enables vertical scrolling at 400px tall, and still exposes the
bottom Save and Cancel actions after scrolling without any RenderFlex overflow.

Fail: any height step throws a framework exception, the form loses visible
content, vertical scrolling is not exposed at 400px, or the bottom actions
cannot be reached after scrolling.
```

# TS-336

Validates that the open **Create issue** form survives a gradual resize from a
desktop viewport to a compact mobile viewport without surfacing RenderFlex
overflow errors or disappearing from the user-visible surface.

The automation:
1. opens the real Create issue form in the widget runtime
2. resizes the same open surface through desktop, tablet, and compact widths
3. checks that the visible form title, key fields, and actions remain rendered
4. drains Flutter framework exceptions after each resize step to catch
   RenderFlex overflow regressions
5. verifies the final compact viewport still renders as a near full-screen form

## Run this test

```bash
flutter test testing/tests/TS-336/test_ts_336.dart
```

## Expected result

```text
Pass: the Create issue form remains visible throughout the desktop-to-mobile
resize path, no Flutter/RenderFlex overflow exception is reported, and the final
compact surface fills the viewport like a mobile full-screen form.

Fail: any resize step throws a framework exception, the form loses visible
content, or the final compact layout stays inset/clipped instead of adapting.
```

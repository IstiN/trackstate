# TS-345

Validates that the open **Create issue** form can hold dense user content while
resizing from a desktop viewport to a compact mobile viewport without surfacing
RenderFlex overflow errors or pushing the visible fields/actions outside the
form surface.

The automation:
1. opens the real Create issue form in the widget runtime
2. enters a long unbroken Summary string and a multi-paragraph Description
3. resizes the same open form through desktop, tablet, and compact widths
4. checks that Summary, Description, Save, and Cancel stay visible, bounded,
   and readable throughout the resize path
5. drains Flutter framework exceptions after each resize step to catch
   overflow-stripe / RenderFlex regressions

## Run this test

```bash
flutter test testing/tests/TS-345/test_ts_345.dart
```

## Expected result

```text
Pass: the Create issue form keeps the typed long Summary and Description, no
Flutter/RenderFlex overflow exception is reported during resize, and the Summary
field, Description field, Save button, and Cancel button all remain within the
visible Create issue surface from 1440px down to 390px.

Fail: any resize step throws a framework exception, loses the typed content, or
renders the key fields/actions outside the visible Create issue surface.
```

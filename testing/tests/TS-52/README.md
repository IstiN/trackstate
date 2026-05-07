# TS-52

Verifies that the visible `Connected` repository-access status on Settings uses the centralized theme success palette hex and that the palette token remains WCAG AA compliant for that button state.

## Install dependencies

```bash
/tmp/flutter/bin/flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-52/connected_status_palette_test.dart
```

## Expected behavior

The visible `Connected` label should match the centralized success palette token instead of a custom color, and that palette hex should remain at or above `4.5:1` contrast against the control background.

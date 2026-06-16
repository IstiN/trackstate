# TS-114

Verifies that the visible `Connected` status badge on the Settings screen uses
the centralized success-background theme token instead of a legacy hardcoded
color.

The automation:
1. opens Settings with a stored GitHub token so the visible `Connected` state is rendered
2. verifies the user-facing `Project Settings` heading is visible
3. verifies exactly one visible `Connected` control is shown in the repository-access section
4. inspects the rendered badge container background and compares it to the centralized success token

## Install dependencies

```bash
/tmp/flutter/bin/flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-114/test_ts_114.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available at `/tmp/flutter/bin/flutter`, or update the commands to
  use your CI Flutter binary

## Expected output when the test passes

```text
00:00 +1: All tests passed!
```

## Expected behavior

The visible `Connected` badge background should match the centralized success
token `#3BBE60` and must not use the legacy hardcoded color `#CD5B3B`.

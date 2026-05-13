# TS-394

Validates that the production-visible **Create issue** form still behaves like a
usable scrollable surface when inline validation expands the layout at the
minimum supported desktop height of `1440x400`.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-394/test_ts_394.dart --reporter expanded
```

## Required environment and config

- Flutter SDK 3.35.3 / Dart 3.9.2 or a compatible stable toolchain
- No additional environment variables or external credentials are required

## Expected result

```text
Pass: submitting the empty Create issue form at 1440x400 renders the visible
summary validation message, increases the scrollable content height without any
RenderFlex overflow exceptions, and keeps Save/Cancel reachable at the bottom of
the scroll view.

Fail: validation text does not appear, the scrollable area does not adapt to the
extra error height, framework overflow exceptions occur, or the bottom actions
stop being fully reachable after validation.
```

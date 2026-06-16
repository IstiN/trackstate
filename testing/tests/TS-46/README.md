# TS-46

TS-46 validates Settings accessibility for the desktop layout.

## What it covers

- Confirms the visible Settings cards render.
- Verifies the runtime/provider controls expose meaningful semantics on the interactive controls.
- Checks keyboard Tab order for the top-bar controls.
- Measures placeholder contrast and the rendered `Connected` label contrast.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test --reporter compact testing/tests/TS-46/settings_accessibility_test.dart
```

## Required environment and config

- Flutter SDK 3.35.3 compatible with the repository toolchain.
- No extra environment variables are required.
- The test uses fixture repositories from `testing/fixtures/repositories/`.
- The robot sets a desktop viewport of `1440x960`.

## Expected passing output

```text
00:00 +0: ...
00:0x +1: All tests passed!
```

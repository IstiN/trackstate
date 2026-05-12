# TS-469

Validates the Settings > Locales translation editor for accessibility and
visual quality against a Local Git repository fixture with multiple locales and
intentional fallback gaps.

The automation:
1. seeds a Local Git repository with English and French localized catalogs
2. opens the production Settings > Locales screen and switches to `fr`
3. checks the visible translation editor content and fallback warning text
4. verifies translation fields expose non-empty semantics labels
5. verifies the fallback warning treatment uses the rendered warning tokens and
   meets the required contrast thresholds
6. verifies empty translation placeholders stay readable
7. verifies keyboard Tab traversal follows the translation matrix order

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-469/test_ts_469.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

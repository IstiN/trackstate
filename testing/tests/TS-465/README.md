# TS-465

Verifies the production Settings > Locales flow enforces default-locale and
last-locale protection rules against a Local Git repository fixture seeded with
`en` as the default locale and `de` as a second configured locale.

The automation:
1. opens `Settings > Locales` and checks the visible user-facing labels for the
   locale management screen
2. verifies `Remove locale` stays disabled while `en` is the current default
3. changes `Default locale` to `de` and confirms the visible default chip and
   dropdown state update
4. verifies `Remove locale` stays disabled while `de` is the selected default
5. selects non-default `en`, removes it, and confirms only `de (default)`
   remains visible
6. verifies `Remove locale` stays disabled for the last remaining locale

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-465/test_ts_465.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

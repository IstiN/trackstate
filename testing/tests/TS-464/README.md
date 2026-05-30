# TS-464

Verifies the production `Settings > Locales` add-locale flow against a Local
Git repository fixture that starts with only `en` configured.

The automation:
1. seeds a Local Git repository whose `project.json.supportedLocales` starts as
   only `en`
2. opens `Settings > Locales` and confirms the locale-management UI is visible
3. requires the Add locale dialog to expose a validated `Locale code` selector,
   then selects `fr` from that list and confirms the add flow
4. verifies the new `fr` locale becomes available for translation editing
5. verifies `DEMO/config/i18n/fr.json` is scaffolded immediately
6. verifies `DEMO/project.json.supportedLocales` includes `fr` immediately

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-464/test_ts_464.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected behavior

This test should pass only when the production Add locale flow:
1. exposes a validated `Locale code` selector,
2. allows selecting `fr`,
3. makes `fr` available for translation editing immediately, and
4. scaffolds `DEMO/config/i18n/fr.json` plus `DEMO/project.json.supportedLocales`
   immediately after confirmation.

If the production-visible dialog still exposes only a free-text `Locale code`
field, the automation records that product defect and still continues through
the visible dialog where possible so the failure output captures whether the UI
and repository updates happened after confirmation.

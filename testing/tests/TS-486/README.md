# TS-486

Verifies the production Local Git runtime persists a saved locale translation in
`Settings > Locales` after the user navigates away and returns to the settings
screen.

The automation:
1. seeds a Local Git repository with distinct `de`, `en`, and canonical labels
   for the `in-progress` status
2. forces the viewer locale to `de` before launching the production app
3. opens `Settings > Locales`, edits the `de` translation from
   `In Bearbeitung` to `WIP`, and saves
4. verifies the persisted `config/i18n/de.json` catalog stores `WIP`
5. navigates to `Board` and confirms the user-visible status column updates to
   `WIP`
6. returns to `Settings > Locales` and verifies the `de` translation field still
   displays `WIP`

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-486/test_ts_486.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

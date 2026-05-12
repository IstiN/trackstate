# TS-467

Verifies the production Local Git runtime resolves status labels in the visible
JQL Search issue list by viewer locale first, then project default locale, and
finally the canonical status name, while refreshes after Settings > Locales
saves without rerunning the search.

The automation:
1. seeds a Local Git repository with `en` default locale, a distinct
   default-locale translation for `in-progress`, and a `de` translation for
   the same status so the test can distinguish default-locale fallback from
   canonical-name fallback
2. forces the viewer locale to `de` before launching the production app
3. opens `JQL Search`, searches `project = DEMO`, and checks the visible
   `DEMO-2` issue row for the localized status label
4. opens `Settings > Locales`, updates the `de` translation from
   `In Bearbeitung` to `WIP`, saves, and verifies the issue row refreshes
   without rerunning the query
5. removes the `de` translation, saves again, and verifies the issue row falls
   back to the distinct default-locale label
6. removes the `en` translation too, saves again, and verifies the issue row
   falls back to the canonical status name

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-467/test_ts_467.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

# TS-487

Verifies the production Local Git runtime falls back to the canonical status
name in the visible JQL Search issue list after both the viewer-locale (`de`)
and default-locale (`en`) translations are cleared from `Settings > Locales`.

The automation:
1. seeds a Local Git repository with distinct `de`, `en`, and canonical labels
   for the `in-progress` status
2. forces the viewer locale to `de` before launching the production app
3. opens `JQL Search`, searches `project = DEMO`, and confirms the visible issue
   row initially uses the viewer-locale label
4. opens `Settings > Locales`, clears the `de` translation, and saves
5. clears the `en` default-locale translation, and saves
6. returns to `JQL Search` and verifies the visible issue row shows the
   canonical status name `In Progress`

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-487/test_ts_487.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

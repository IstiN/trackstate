# TS-226

Validates that Local Git handles a missing `DEMO/config/fields.json`
gracefully by surfacing a visible fallback warning and keeping the
production-visible `Create issue` flow usable with the core system fields.

The automation:
1. creates a clean Local Git repository fixture and removes
   `DEMO/config/fields.json`
2. launches the real `TrackStateApp` in Local Git mode against that fixture
3. waits for the missing-config path to surface a visible fallback warning
4. verifies the app stays in a visible Local Git runtime state without a data
   load failure
5. opens the production-visible `Create issue` flow and checks the fallback
   `Summary`, `Description`, `Save`, and `Cancel` controls
6. enters text into the core fields and verifies those inputs remain usable

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-226/test_ts_226.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the missing fields.json path reports a visible fallback warning, Local Git
stays usable, and the Create issue form still renders Summary, Description,
Save, and Cancel so the user can continue with the core fallback fields.

Fail: the app surfaces a data load failure, leaves the user without a visible
Local Git runtime, or the Create issue form is missing one or more core
controls.
```

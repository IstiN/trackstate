# TS-240

Validates that Local Git shows a visible fallback warning message when
`DEMO/config/fields.json` is missing and still renders the production-visible
`Create issue` form with the default system fields.

The automation:
1. reuses the TS-226 Local Git fixture and removes `DEMO/config/fields.json`
2. launches the real `TrackStateApp` in Local Git mode against that fixture
3. waits for the visible fallback warning banner to mention built-in defaults
   and the missing `fields.json` path
4. verifies the Local Git runtime remains usable without a data load failure
5. opens the production-visible `Create issue` flow and checks the fallback
   `Summary`, `Description`, `Save`, and `Cancel` controls

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-240/test_ts_240.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the missing fields.json path shows the repository-config fallback warning,
Local Git stays visible, and the Create issue form still renders Summary,
Description, Save, and Cancel.

Fail: the warning banner is missing or generic enough that it does not mention
the fallback and missing fields.json state, the app surfaces a data load
failure, or the Create issue form loses one or more core controls.
```

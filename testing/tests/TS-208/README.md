# TS-208

Validates that Local Git handles a malformed `DEMO/config/fields.json`
gracefully by reporting the parse failure and keeping the production-visible
`Create issue` flow usable with the core system fields.

The automation:
1. creates a clean Local Git repository fixture whose `DEMO/config/fields.json`
   contains invalid JSON
2. launches the real `TrackStateApp` in Local Git mode against that fixture
3. waits for the malformed-config path to emit a visible parse-error message
4. verifies the app still stays in a visible Local Git runtime state
5. opens the production-visible `Create issue` flow and checks the fallback
   `Summary`, `Description`, `Save`, and `Cancel` controls
6. enters text into the core fields and verifies those inputs remain usable

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-208/test_ts_208.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the malformed fields.json path reports the parsing error, Local Git stays
usable, and the Create issue form still renders Summary, Description, Save, and
Cancel so the user can continue with the core fallback fields.

Fail: the parsing error is not reported, the app leaves the user without a
visible Local Git runtime, or the Create issue form is missing one or more core
controls.
```

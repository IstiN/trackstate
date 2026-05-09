# TS-239

Validates that Local Git handles a missing `DEMO/config` directory by staying
usable, surfacing the fallback warning, and keeping the production-visible
`Create issue` flow available with the core system fields.

The automation:
1. creates a clean Local Git repository fixture and deletes `DEMO/config`
2. launches the real `TrackStateApp` in Local Git mode against that fixture
3. waits for the visible fallback warning instead of asserting immediately
4. verifies the Local Git runtime remains visible without a data-load crash
5. opens the production-visible `Create issue` flow
6. checks the fallback `Summary`, `Description`, `Save`, and `Cancel` controls
7. enters text into the core fields and verifies those values remain visible

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-239/test_ts_239.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the missing config directory surfaces a visible fallback warning, Local
Git stays usable, and the Create issue form still renders Summary, Description,
Save, and Cancel so the user can continue with the core fallback fields.

Fail: the app crashes, surfaces a data load failure, leaves the user without a
visible Local Git runtime, or the Create issue form is missing one or more core
controls.
```

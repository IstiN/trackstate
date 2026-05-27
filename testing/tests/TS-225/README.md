# TS-225

Validates that a malformed `DEMO/config/fields.json` does not make the app lose
its visible Local Git runtime context or regress the repository-access surface
to an AI-only provider state.

The automation:
1. creates a clean Local Git repository fixture whose `fields.json` is invalid
2. launches the real `TrackStateApp` in Local Git mode against that fixture
3. waits for the malformed-config path to emit a visible parse-error message
4. verifies the user-visible repository access surface still shows `Local Git`
   in the main UI and top bar instead of `Connect GitHub` or an AI-only state
5. opens the production-visible Local Git runtime dialog and checks the
   repository path and branch shown to the user

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-225/test_ts_225.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: the malformed fields.json path reports the parse error, the Local Git
runtime remains visible in the UI, and the repository access dialog still opens
with Local Git details.

Fail: the parse error is not reported, the UI loses the Local Git provider
state, the repository-access chrome regresses to Connect GitHub / AI-only
semantics, or opening the visible Local Git dialog throws an exception.
```

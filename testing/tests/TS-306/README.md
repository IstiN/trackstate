# TS-306

Validates that provider-backed `Create issue` failures are surfaced to the user
and that the entered draft remains available for correction and retry.

The automation:
1. creates a provider-backed repository fixture that exposes the real create
   issue flow and throws a typed provider failure from the shared mutation layer
2. launches the real `TrackStateApp` through the shared
   `TrackStateAppComponent`
3. opens the production-visible `Create issue` flow
4. enters `Summary`, `Description`, and two `Labels`
5. saves the issue and waits for the provider-backed failure state to render
6. verifies the visible failure banner includes both `Save failed:` and the
   typed provider error message
7. verifies the form stays open with `Summary`, `Description`, and both labels
   still visible

The ticket uses the shared `TrackStateAppComponent` abstraction and keeps all
logic under `testing/`.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
/tmp/flutter/bin/flutter test testing/tests/TS-306/test_ts_306.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`, or use the explicit `/tmp/flutter/bin/flutter`
  path shown above
- No extra environment variables are required

## Expected result

```text
Pass: the create issue save failure is surfaced to the user and the open form
retains the typed Summary, Description, and Labels so the user can correct and
retry.

Fail: the create issue action does not reach the shared mutation layer, the
failure banner is missing or hides the provider error, or the draft values are
lost after the failed save.
```

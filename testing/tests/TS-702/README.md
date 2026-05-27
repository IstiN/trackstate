# TS-702

Validates that a returning user can start onboarding from the persistent
`Add workspace` action in the active app shell.

The automation:
1. seeds an active saved workspace profile for a returning user
2. launches the production app shell directly into that workspace
3. verifies the `Add workspace` action is visible beside the workspace switcher
4. clicks `Add workspace` and verifies the onboarding screen opens

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-702/test_ts_702.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: returning users see a persistent Add workspace action in the active shell
near the workspace switcher, and clicking it opens onboarding.

Fail: the active shell does not expose Add workspace, the action is not placed
with the primary shell controls near the workspace switcher, or clicking it does
not open onboarding.
```

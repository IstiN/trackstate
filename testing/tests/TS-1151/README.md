# TS-1151

Validates the first-launch onboarding flow for a fresh user with no saved
workspace profiles and checks that the hosted setup path is actually available.

The automation:
1. launches the production onboarding screen with empty SharedPreferences
2. verifies the first screen shows both `Local folder` and `Hosted repository`
3. switches to `Hosted repository`
4. verifies the hosted form visibly renders the hosted `Repository` and
   `Branch` fields plus the repository helper copy
5. tabs through the rendered controls to confirm the keyboard path reaches the
   hosted setup inputs in logical order

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-1151/test_ts_1151.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required

## Expected result

```text
Pass: a fresh first-launch user can see both onboarding choices, switch to the
hosted flow, see visible Repository and Branch inputs plus the repository
helper copy, and reach those controls with the keyboard.

Fail: the hosted choice is missing, the hosted form does not render the
hosted Repository/Branch contract, or the keyboard path does not traverse the
hosted controls in logical order.
```

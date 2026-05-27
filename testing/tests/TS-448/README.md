# TS-448

Validates that a mandatory hosted bootstrap GitHub rate-limit failure keeps the
real TrackState shell visible, surfaces the startup recovery container inside
Settings, and prevents navigation away from Settings until bootstrap succeeds.

The automation:
1. launches the hosted setup runtime with a ticket-specific fixture that returns
   a 403 GitHub rate-limit response on the first `project.json` or
   `.trackstate/index/issues.json` fetch
2. verifies the shell still shows the visible navigation chrome, Project
   Settings content, and recovery messaging instead of collapsing to a blocking
   recovery-only surface
3. attempts to use **Dashboard** and **Board** while recovery is active and
   confirms those controls stay inert
4. taps **Retry** and verifies the hosted bootstrap succeeds on the next load
5. confirms **Dashboard** and **Board** become usable again after recovery

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-448/test_ts_448.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test uses a hosted mock GitHub repository fixture with first-request
  rate-limit failures for mandatory bootstrap artifacts

## Expected result

```text
Pass: the hosted shell remains visible with navigation chrome and Project
Settings recovery content after a mandatory bootstrap rate-limit error, the
Dashboard and Board controls do not navigate away while recovery is active, and
Retry restores normal navigation once bootstrap succeeds.

Fail: the app falls back to a dedicated recovery-only surface, the navigation
chrome is missing, the non-Settings navigation items remain interactive during
recovery, or Retry does not restore Dashboard and Board navigation.
```

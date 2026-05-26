# TS-443

Validates that a GitHub 403 rate-limit response during mandatory hosted
bootstrap is classified as a dedicated startup recovery state instead of a
generic load failure.

The automation:
1. reuses the TS-448 hosted mandatory-bootstrap fixture for both blocking
   artifacts: `TRACK/project.json` and `TRACK/.trackstate/index/issues.json`
2. verifies the model-level recovery metadata exposes the GitHub rate-limit
   category, reset timestamp, blocking bootstrap readiness state, and hosted
   recovery action contract
3. invokes the model-level retry path and confirms the next bootstrap attempt
   succeeds
4. pumps the real app and verifies the blocking recovery surface shows the
   expected Retry and Connect GitHub actions, opens the auth dialog, and clears
   after Retry

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-443/test_ts_443.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- No extra environment variables are required
- The test uses the hosted mock GitHub repository fixture from TS-448

## Expected result

```text
Pass: mandatory bootstrap 403 responses create GitHub rate-limit startup
recovery metadata with a valid retry timestamp, keep bootstrap readiness in the
blocking state, expose Retry and Connect GitHub actions, and recover on the
next retry.

Fail: the app falls back to a generic load failure, publishes bootstrap-ready
state too early, omits either recovery action, or Retry does not recover the
startup flow.
```

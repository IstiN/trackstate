# TS-701

Automates the first-launch onboarding regression for a fresh workspace state with no saved or migrated workspaces.

## What this test verifies

1. Launches `TrackStateApp` with an empty SharedPreferences-backed workspace profile store.
2. Confirms first launch opens onboarding instead of the dashboard.
3. Verifies the visible first-run UI includes `Local folder` and `Hosted repository`.
4. Verifies those choices are exposed as equal first-class options in the same row with user-facing semantics.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-701/test_ts_701.dart --reporter expanded
```

## Required configuration

- Flutter SDK available on `PATH`
- No additional environment variables are required

## Expected passing output

```text
00:00 +0: loading /home/runner/work/trackstate/trackstate/testing/tests/TS-701/test_ts_701.dart
00:00 +1: All tests passed!
```

## Assertions

- fresh launch opens onboarding with no saved or migrated workspaces
- `Local folder` and `Hosted repository` are present as the ticket-required choices
- the two choices are exposed as equal first-class options

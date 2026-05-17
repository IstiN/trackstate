# TS-701

Validates first-launch onboarding in a fresh workspace state.

The automation:
1. launches TrackState with an empty SharedPreferences-backed workspace profile store
2. confirms first launch opens the onboarding route instead of the dashboard
3. checks that `Local folder` and `Hosted repository` are visible
4. verifies those choices are exposed as equal primary options in the same row

## Run this test

```bash
flutter test testing/tests/TS-701/test_ts_701.dart --reporter expanded
```

## Required configuration

- Flutter SDK available on PATH

## Assertions

- fresh launch opens onboarding with no saved or migrated workspaces
- `Local folder` and `Hosted repository` are present as the ticket-required choices
- the two choices are exposed as equal first-class options

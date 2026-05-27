# TS-222

Validates that switching storage from `Local Git` back to hosted/remote mode
re-initializes the Dashboard top bar and the Settings repository-access surface
without a manual refresh.

The automation:
1. starts the real app in hosted mode and confirms the top bar exposes
   `Connect GitHub`
2. switches the app into a valid `Local Git` state using a temporary repository
   fixture and the `main` write branch
3. confirms the Local Git values are retained in `Settings`
4. returns to `Dashboard` and verifies the top bar shows `Local Git`
5. opens `Settings` and attempts the production-visible reverse switch back to
   hosted mode
6. verifies the Dashboard top bar returns to hosted mode and removes the
   `Local Git` indicator
7. verifies `Settings` shows the hosted repository-access status (`Connect GitHub`
   or `Connected`) together with the hosted token field instead of the Local Git
   repository fields
8. opens the hosted `Connect GitHub` dialog from the top bar and confirms the
   visible user-facing controls

The ticket uses the shared `TrackStateAppComponent` abstraction and keeps all
logic under `testing/`.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-222/test_ts_222.dart --reporter expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected result

```text
Pass: the app exposes a visible hosted-mode selector after leaving Local Git,
re-renders the Dashboard top bar back to hosted mode, and shows the hosted
repository-access status in Settings without a manual refresh.

Fail: Settings never exposes a hosted selector after Local Git, the Dashboard
stays in Local Git mode, or the hosted repository-access status does not appear
after the reverse switch.
```

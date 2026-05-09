# TS-221

Validates that switching storage from hosted mode to `Local Git` rebuilds the
Dashboard top bar immediately, removing hosted-only UI such as `Connect GitHub`
without a manual refresh.

The automation:
1. starts the real app in hosted mode
2. opens `Dashboard` and verifies a visible top-bar `Connect GitHub` control
3. switches storage in `Settings` to `Local Git` using a temporary repository
   fixture and a `main` write branch
4. confirms the saved `Repository Path` and `Write Branch` values remain visible
   in `Settings`, then proves the apply boundary in-place: it taps a visible
   `Save` action when one exists, otherwise it asserts the top bar already shows
   `Local Git` while the user is still on `Settings`
5. returns to `Dashboard` immediately without refreshing the app
6. verifies the hosted `Connect GitHub` control is no longer visible in the top
   bar and that `Local Git` is shown instead
7. opens the `Local Git` runtime dialog and verifies the repository path and
   branch presented to the user match the saved settings
8. fails with top-bar, visible-text, and semantics snapshots when the runtime UI
   remains stale after the storage switch

The ticket uses the shared `TrackStateAppComponent` abstraction and keeps all
logic under `testing/`.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-221/test_ts_221.dart --reporter expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected result

```text
Pass: switching Settings from hosted mode to Local Git applies from the real
user-visible boundary in Settings, updates the Dashboard top bar immediately,
replaces Connect GitHub with Local Git, and exposes the saved repository path
and branch through the Local Git runtime dialog.

Fail: Dashboard still shows hosted-mode controls after the settings switch, does
not expose Local Git immediately, or the Local Git runtime dialog does not show
the saved repository path and branch.
```

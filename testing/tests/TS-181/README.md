# TS-181

Validates that the top-bar `Create issue` entry point stays visible and
reachable after switching the app from hosted storage to `Local Git`.

The automation:
1. starts the real app in hosted mode
2. opens `Dashboard` and verifies a visible top-bar `Create issue` control
3. opens the create flow and confirms the user-facing `Summary`,
   `Description`, `Save`, and `Cancel` controls
4. switches storage in `Settings` to `Local Git` using a temporary repository
   fixture and a `main` write branch
5. returns to `Dashboard` and verifies the top bar reflects `Local Git`
   without a manual refresh
6. verifies `Create issue` remains visible and user-reachable after the switch
7. fails with top-bar, visible-text, and semantics snapshots when the runtime
   label or create entry point does not match the expected user-facing state

The ticket uses the shared `TrackStateAppComponent` abstraction and keeps all
logic under `testing/`.

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
flutter test testing/tests/TS-181/test_ts_181.dart --reporter expanded
```

## Required configuration

This test creates its own temporary local Git-backed TrackState repository
fixture, so no external credentials or environment variables are required.

## Expected result

```text
Pass: the app switches the top-bar storage indicator from hosted mode to Local
Git without a manual refresh, and Create issue stays visible and reachable from
Dashboard after the switch.

Fail: the top bar stays in hosted mode, does not show Local Git after the
settings change, or Create issue is no longer visible or reachable after the
switch.
```

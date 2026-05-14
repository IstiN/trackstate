# TS-725

Verifies the ticketed workspace combination in a supported runtime:
one **active local** workspace and one **inactive hosted** workspace.

The automation:
1. seeds the production workspace profile store with one active local workspace
   and one inactive hosted workspace
2. launches the production tracker in a Flutter widget runtime that can open
   the local repository
3. opens **Workspace switcher** and checks the active local row shows
   `Local Git`
4. checks the inactive hosted row shows `Needs sign-in` and does not show
   `Connected`, `Read-only`, or `Attachments limited`
5. opens **Settings** from the active local workspace and looks for the
   production GitHub sign-in controls needed to continue the ticket flow

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-725/test_ts_725.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- Linux widget-test environment

## Expected result

```text
Pass: the active local row shows Local Git, the inactive hosted row shows
Needs sign-in, and the app exposes a supported sign-in path from the active
local workspace so the switcher can be rechecked after authentication.
```

## Current product gap captured by this automation

```text
Fail: the supported active local runtime does not expose a visible Connect
GitHub / Repository access control, so the sign-in step from the active local
workspace cannot be executed.
```

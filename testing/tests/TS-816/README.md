# TS-816

Verifies that clicking **Connect GitHub** on an **inactive local workspace**
entry starts the signed-out authentication flow.

The automation:
1. seeds the production workspace profile store with two valid local workspaces
   and leaves the second one inactive
2. launches the production tracker through the shared
   `TrackStateAppComponent`
3. opens **Workspace switcher** and identifies the inactive local row
4. clicks that same row's `Connect GitHub` control
5. verifies the **Connect GitHub** dialog appears with the expected
   authentication controls

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-816/test_ts_816.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- Linux widget-test environment

## Expected result

```text
Pass: the inactive local workspace row is visible as a non-active local
workspace and clicking Connect GitHub opens the Connect GitHub authentication
dialog while signed out.
```

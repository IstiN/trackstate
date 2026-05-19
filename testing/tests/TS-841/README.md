# TS-841

Verifies that pressing **Arrow Up** in **Workspace switcher** moves the active
selection from the second saved workspace to the previous one and keeps the
switcher open.

The automation:
1. seeds the production workspace profile store with two valid local workspaces
   and preselects the second workspace
2. launches the production tracker through the shared `TrackStateAppComponent`
3. opens **Workspace switcher** and confirms the second row is visibly active
4. presses **Arrow Up** directly from that preconditioned state
5. verifies the first workspace becomes active, keyboard focus moves to that
   previous row, and the switcher panel stays open

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-841/test_ts_841.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- Linux widget-test environment

## Expected result

```text
Pass: with the second saved workspace active, pressing Arrow Up moves the
selection and keyboard focus to the previous workspace and leaves the
workspace switcher open.
```

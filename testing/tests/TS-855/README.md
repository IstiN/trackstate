# TS-855

Verifies that pressing **Arrow Up** in the **Workspace switcher** moves the
active selection from the second saved workspace to the previous one and moves
programmatic keyboard focus to that previous workspace row instead of leaving
focus on the parent desktop switcher container.

The automation:
1. seeds the production workspace profile store with two valid local workspaces
   and preselects the second workspace
2. launches the production tracker through the shared `TrackStateAppComponent`
3. opens **Workspace switcher** and confirms the second row is visibly active
4. presses **Arrow Up** directly from that preconditioned state
5. verifies the first workspace becomes active, the switcher panel stays open,
   and `primaryFocus` matches the previous workspace row instead of
   `desktop-workspace-switcher`

## Install dependencies

```bash
flutter pub get
```

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-855/test_ts_855.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- Linux widget-test environment

## Expected result

```text
Pass: with the second saved workspace active, pressing Arrow Up moves the
selection to the first workspace, keeps the workspace switcher open, and moves
primaryFocus to workspace-switcher-row-summary-<first workspace id> instead of
desktop-workspace-switcher.
```

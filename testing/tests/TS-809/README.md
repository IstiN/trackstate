# TS-809

Verifies an inactive local workspace entry in **Workspace switcher** keeps a
visible **Connect GitHub** entry point while the user is signed out.

The automation:
1. seeds the production workspace profile store with two valid local workspaces
   and leaves the second one inactive
2. launches the production tracker through the shared `TrackStateAppComponent`
3. opens **Workspace switcher** and identifies the inactive local row using only
   the ticket-relevant conditions: visible, local, and not active
4. verifies that same inactive local row visibly renders `Connect GitHub`

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-809/test_ts_809.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- Linux widget-test environment

## Expected result

```text
Pass: the inactive local workspace row is visible as a non-active local
workspace and keeps a visible Connect GitHub control while signed out.
```

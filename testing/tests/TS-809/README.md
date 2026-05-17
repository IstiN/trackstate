# TS-809

Verifies an inactive local workspace entry in **Workspace switcher** keeps a
visible **Connect GitHub** entry point while the user is signed out.

The automation:
1. seeds the production workspace profile store with two valid local workspaces
   and leaves the second one inactive
2. launches the production tracker in the supported Flutter widget runtime
3. opens **Workspace switcher** and confirms the inactive local row still shows
   `Local Git` plus its normal inactive-row controls
4. verifies that same inactive local row visibly renders `Connect GitHub`
5. clicks `Connect GitHub` from that row and treats the scenario as successful
   only if the production auth dialog exposes the `Fine-grained token` field and
   `Connect token` action

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-809/test_ts_809.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- Linux widget-test environment

## Expected result

```text
Pass: the inactive local workspace row shows Local Git, keeps a visible Connect
GitHub control while signed out, and clicking it opens the production
authentication dialog.
```

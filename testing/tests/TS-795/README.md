# TS-795

Verifies the active local workspace entry in **Workspace switcher** keeps a
visible **Connect GitHub** entry point while the user is signed out.

The automation:
1. seeds the production workspace profile store with one active local workspace
   and one inactive hosted workspace
2. launches the production tracker in the supported Flutter widget runtime
3. opens **Workspace switcher** and confirms the active local row still shows
   `Local Git`
4. verifies the same active local row visibly renders `Connect GitHub`
5. clicks `Connect GitHub` from that row and treats the scenario as successful
   only if the production auth dialog exposes the `Fine-grained token` field and
   `Connect token` action

## Run this test

```bash
mkdir -p outputs && flutter test testing/tests/TS-795/test_ts_795.dart --reporter expanded
```

## Required environment and config

- Flutter SDK available on `PATH`
- Linux widget-test environment

## Expected result

```text
Pass: the active local workspace row shows Local Git, keeps a visible Connect
GitHub control while signed out, and clicking it opens the production
authentication dialog.
```

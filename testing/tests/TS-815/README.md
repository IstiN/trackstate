# TS-815 test automation

Verifies that the production TrackState workspace switcher renders a visible
row-level `Connect GitHub` control on all saved local workspace rows
simultaneously while the user is signed out.

## Run this test

```bash
flutter test testing/tests/TS-815/test_ts_815.dart --reporter expanded
```

## Expected result

```text
Pass: the workspace switcher shows one active local workspace row and at least
two inactive local workspace rows, and every row exposes its own visible
Connect GitHub control at the same time.

Fail: any local workspace row is missing its row-level Connect GitHub control,
or the signed-out switcher does not render the expected active/inactive local
rows simultaneously.
```

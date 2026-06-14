# TS-1346 test automation

Verifies that `.github/workflows/build-native.yml` functions as a thin wrapper
that dispatches the reusable `.github/workflows/build-macos-reusable.yml`
workflow.

## What is tested

1. The workflow declares a `workflow_dispatch` trigger.
2. Jobs `resolve-release`, `build-macos`, and `publish-release` are present.
3. The `build-macos` job uses `uses: ./.github/workflows/build-macos-reusable.yml`.
4. Required inputs `release_tag`, `release_checkout_ref`, and `build_number` are
   passed from `resolve-release` outputs.

## Run this test

```bash
python -m unittest testing.tests.TS-1346.test_ts_1346
```

# TS-1343 test automation

Verifies that the platform build jobs in `.github/workflows/release-on-main.yml`
are blocked when the shared validation job fails by declaring `needs: validate`.

## What is tested

1. The workflow file exists and is valid YAML.
2. The workflow declares `push` and `workflow_dispatch` triggers.
3. Jobs `resolve-version`, `validate`, `build-linux`, `build-windows`,
   `build-macos`, and `publish-release` are present.
4. Each platform build job lists both `resolve-version` and `validate` in its
   `needs` clause.
5. The final `publish-release` job depends on all three platform build jobs.

## Run this test

```bash
python -m unittest testing.tests.TS-1343.test_ts_1343
```

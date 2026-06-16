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
5. When a self-hosted macOS release runner is online, the test dispatches
   `build-native.yml` via `workflow_dispatch` using `release_ref=v0.0.98` (the
   same input the repair workflow uses) and verifies the run completes
   successfully.
6. If the required self-hosted runner or GitHub token is unavailable, the test
   reports `blocked_by_human` instead of failing.

## Run this test

```bash
python -m unittest testing.tests.TS-1346.test_ts_1346
```

## Required environment

- `GH_TOKEN` or `GITHUB_TOKEN` with read access to repository runners and
  workflow runs.
- A self-hosted GitHub Actions runner registered to the target repository with
  labels `self-hosted`, `macOS`, `trackstate-release`, and `ARM64`.

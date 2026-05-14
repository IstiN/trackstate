# TS-707

Exercises the live **Apple Release Builds** workflow and verifies that the
macOS release path enforces the expected toolchain contract before any desktop
or CLI build work proceeds.

The automation:
1. clones the repository into a disposable temp directory
2. changes only the workflow's Flutter version in that disposable copy from
   `3.35.3` to `3.30.0`
3. pushes a disposable `v*` tag to trigger the real Apple release workflow
4. waits for the self-hosted macOS build job to start and expose
   `Verify runner toolchain`
5. checks that the validation step fails with the explicit Flutter `3.35.3`
   requirement and that later macOS build steps do not run

## Run this test

```bash
PYTHONPATH=. python3 testing/tests/TS-707/test_ts_707.py
```

## Required environment and preconditions

- GitHub CLI authenticated with permissions to read workflow runs and push the
  disposable tag used by the probe
- Playwright with Chromium available for the workflow-file page verification
- An online self-hosted macOS runner matching the release workflow labels
  (`self-hosted`, `macOS`, `trackstate-release`, `ARM64`)

If the workflow stops in `Verify macOS runner availability` before the build
job starts, the test reports an unmet infrastructure precondition instead of
filing product-bug evidence for TS-707.

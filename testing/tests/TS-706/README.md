# TS-706

Validates that the live `Apple Release Builds` workflow fails fast in its Ubuntu
preflight gate when no TrackState macOS release runner matching the configured
label contract is available.

The automation creates a disposable semantic version tag on `main`, waits for
the resulting workflow run to complete, verifies the preflight and downstream
job outcomes through the GitHub API/logs, and opens the run/job pages in
Chromium for human-style verification.

## Dependencies

- GitHub CLI authenticated with repository and workflow access for
  `IstiN/trackstate`
- Playwright Python package and browser runtime for GitHub Actions page checks

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-706/test_ts_706.py
```

## Config

`config.yaml` is the source of truth for:

- repository and workflow metadata
- preflight/downstream job display names
- expected Ubuntu runner and macOS label contract
- polling and UI timeout values

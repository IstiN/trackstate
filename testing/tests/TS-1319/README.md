# TS-1319

Verifies that the live `Apple Release Builds` workflow does not hang in its Ubuntu preflight readiness gate when the infrastructure check is slow or blocked.

The automation:

1. creates a disposable semantic version tag on `IstiN/trackstate`
2. waits for the resulting workflow run to complete
3. checks that the preflight job ends after roughly five minutes with a failure/timeout result
4. opens the GitHub Actions run and job pages for human-style verification

## Run

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1319/test_ts_1319.py
```

## Requirements

- `GH_TOKEN` or `GITHUB_TOKEN` with repo and workflow access to `IstiN/trackstate`
- GitHub CLI authenticated for API and tag creation
- Chromium/Playwright for the GitHub Actions page checks

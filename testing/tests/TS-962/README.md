# TS-962 test automation

This test verifies that the live `Flutter Required Checks` pull-request workflow
still attempts the `log-validation` step after the run is manually cancelled
while `Run axe-core accessibility checks` is in progress.

The automation:

1. creates a disposable pull request that changes only `testing/accessibility`
   files
2. keeps the hosted accessibility scan step running long enough to cancel the
   workflow
3. requests cancellation against the live pull-request run
4. verifies the cancelled run still exposes `log-validation` as attempted rather
   than skipped
5. performs contributor-visible verification on the GitHub Actions run page and
   workflow file page with Playwright

## Install dependencies

```bash
python -m pip install -r testing/requirements.txt
playwright install --with-deps chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-962/test_ts_962.py
```

## Required configuration

- GitHub CLI authenticated (`gh auth status`) with push access to
  `IstiN/trackstate`
- `GH_TOKEN`/`GITHUB_TOKEN` available for `gh api`, `gh pr`, and `gh run`
- Playwright Chromium available for contributor-visible GitHub page checks
- network access to `api.github.com`, `github.com`, pull requests, workflow
  logs, and workflow run pages

## Expected passing output

```text
TS-962 passed
```

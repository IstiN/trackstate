# TS-951

Validates the live GitHub Actions accessibility workflow for
`IstiN/trackstate` when a disposable pull request forces the axe-core step to
fail.

The test:

1. creates a disposable PR that changes only `testing/accessibility` probe files
2. waits for the pull-request workflow to complete in a failed state
3. inspects the live workflow contract for the `log-validation` step
4. opens the GitHub Actions run and workflow pages through the standard
   Playwright-backed page factory for human-style verification
5. confirms whether `log-validation` is configured with `always()` and still
   executes after the failing accessibility step

## Install dependencies

```bash
python -m pip install playwright
playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-951/test_ts_951.py
```

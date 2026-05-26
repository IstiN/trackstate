# TS-422 test automation

Validates the deployed hosted startup behavior when `.trackstate/index/issues.json`
is missing from the repository tree presented to the app.

The automation:
1. opens the deployed hosted app in Chromium with a Playwright GitHub API route
   interceptor
2. removes `DEMO/.trackstate/index/issues.json` from the recursive tree response
3. verifies the app does not silently hydrate issue `main.md` files as a
   fallback
4. verifies the user sees a recoverable failure state with `Retry` and visible
   guidance to regenerate the tracker indexes

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-422/test_ts_422.py
```

## Required environment and config

- network access to the hosted app and the public GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: hosted startup fails explicitly, keeps the failure visible with Retry and
index-regeneration guidance, and does not silently read issue main.md files as a
fallback.

Fail: the app silently falls back to issue-file hydration/tree replay, or the
visible failure state does not expose Retry plus regeneration guidance.
```

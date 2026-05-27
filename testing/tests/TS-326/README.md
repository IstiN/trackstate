# TS-326 test automation

Verifies that entering the mixed-case free-text term `eXpLoRe` in the hosted
**JQL Search** screen returns the matching DEMO-2 issue from the live setup
repository.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-326/test_ts_326.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`
- Optional overrides:
  - `TRACKSTATE_LIVE_APP_URL`
  - `TRACKSTATE_LIVE_SETUP_REPOSITORY`
  - `TRACKSTATE_LIVE_SETUP_REF`
  - `TS326_RESULT_PATH`

## Expected result

```text
Pass: The hosted JQL Search page preserves the mixed-case query, shows the
visible "1 issue" summary, and keeps DEMO-2 / Explore the issue board as the
only visible search result.

Fail: The query changes unexpectedly, the result count does not narrow to
"1 issue", or DEMO-2 is not the sole visible result.
```

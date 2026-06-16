# TS-328 test automation

Verifies that submitting an empty query in the hosted **JQL Search** screen does
not filter the result set and keeps every live repository issue visible to the
user.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-328/test_ts_328.py
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
  - `TS328_RESULT_PATH`

## Expected result

```text
Pass: The hosted JQL Search page keeps the query field empty, shows the full
live issue count, and lists every live issue key and summary from the setup
repository.

Fail: The query changes unexpectedly, the issue count stays filtered, or any
live issue key/summary is missing from the visible result list.
```

# TS-327 test automation

Verifies that the hosted **JQL Search** experience returns every live issue whose
content matches `discovery` in the summary, description, or acceptance criteria,
and that the user-facing result count stays in sync with those matches.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-327/test_ts_327.py
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
  - `TS327_RESULT_PATH`

## Expected result

```text
Pass: The live repository contains the seeded Discovery matches, the hosted JQL
Search field keeps the query visible, the result count matches the live corpus,
and only the matching issues remain visible to the user.

Fail: The seeded Discovery coverage is missing, the result count is wrong, or
the visible JQL Search results stay unchanged instead of reflecting the query.
```

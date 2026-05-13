# TS-391 test automation

Verifies the hosted **Comments** tab only shows an edited timestamp marker when a
comment's `updated` metadata differs from `created`.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-391/test_ts_391.py
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
  - `TS391_RESULT_PATH`

## Expected result

```text
Pass: The untouched comment row shows only the created timestamp, and the edited
comment row shows the created timestamp plus a visible Edited timestamp marker.

Fail: The untouched row still shows edited metadata, the edited row hides the
edited marker, or the visible row lookup cannot prove the body and metadata come
from the same rendered comment card.
```

# TS-1137 test automation

Verifies that the live hosted **Settings** flow does **not** report a false
success when the user clicks **Save settings** without changing the Statuses or
Workflows catalogs.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1137/test_ts_1137.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- `TRACKSTATE_LIVE_APP_URL` pointing at the deployed hosted TrackState app
- Defaults come from `testing/core/config/live_setup_test_config.py`

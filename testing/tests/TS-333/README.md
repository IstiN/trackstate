# TS-333 test automation

## Install dependencies

```bash
python -m pip install playwright pillow
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-333/test_ts_333.py
```

## Required environment

- Python 3.12+
- Playwright for Python with Chromium installed
- Pillow installed for screenshot-based color sampling
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`
- Optional overrides:
  - `TRACKSTATE_LIVE_APP_URL`
  - `TRACKSTATE_LIVE_SETUP_REPOSITORY`
  - `TRACKSTATE_LIVE_SETUP_REF`

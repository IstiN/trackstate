# TS-911 test automation

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-911/test_ts_911.py
```

## Required environment

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`
- Optional overrides:
  - `TRACKSTATE_LIVE_APP_URL`
  - `TRACKSTATE_LIVE_SETUP_REPOSITORY`
  - `TRACKSTATE_LIVE_SETUP_REF`

## Coverage notes

- Uses the default desktop viewport of `1440x960`.
- Opens the live workspace switcher from a focused trigger and derives the current last internal keyboard target from the panel's observed in-panel controls.
- Establishes the ticket precondition from the live initial focus state or a real `Tab` from the focused trigger, then presses `Shift+Tab` from that reached first internal target.

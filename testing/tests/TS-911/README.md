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

- Uses the ticket-linked desktop viewport of `1440x900`.
- Opens the live workspace switcher from a focused trigger and captures supporting forward-`Tab` evidence when available without making it a blocker for the ticketed `Shift+Tab` assertion.
- Preserves the selected saved-workspace row as the first internal target when the live panel already opens with focus there; otherwise it focuses the derived first internal target directly through the page object.
- Keeps the final pass/fail decision scoped to the ticketed single-step `Shift+Tab` assertion while deriving the reverse-wrap target from switcher-owned live keyboard-reachable controls only.

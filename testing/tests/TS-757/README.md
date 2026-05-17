# TS-757

Validates that startup with an empty workspace list automatically redirects the
user to **Project Settings**.

The automation:
1. opens the deployed TrackState web app in Chromium with an empty browser
   storage state
2. verifies the app starts with no saved workspaces configured, accepting either
   absent storage keys or an empty normalized workspace-state payload
3. waits for startup initialization to resolve past the splash screen
4. checks whether the final landing screen is **Project Settings** rather than
   the tracker dashboard
5. records a screenshot and the rendered UI text when the expected redirect does
   not occur

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-757/test_ts_757.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- Defaults come from `testing/core/config/live_setup_test_config.py`
- Optional overrides:
  - `TRACKSTATE_LIVE_APP_URL`
  - `TRACKSTATE_LIVE_SETUP_REPOSITORY`
  - `TRACKSTATE_LIVE_SETUP_REF`

## Expected result

```text
Pass: startup dismisses the TrackState.AI splash screen and automatically lands
the user on Project Settings so a new workspace can be added.

Fail: startup resolves into the tracker dashboard, remains on the splash screen,
or otherwise does not expose the Project Settings landing screen when no
workspaces are configured.
```

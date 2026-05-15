# TS-763

Validates that directly opening the deployed app at the dashboard route with no
saved workspaces triggers the navigation guard and redirects the user to
**Project Settings**.

The automation:
1. opens the deployed TrackState web app in Chromium at `/#/dashboard` inside a
   fresh browser context
2. verifies the browser starts with no saved workspaces configured, accepting
   either absent storage keys or an empty normalized workspace-state payload
3. waits for startup initialization to resolve past the splash screen
4. checks that the final landing screen is **Project Settings** and that the app
   no longer remains on the dashboard route
5. records a screenshot and the rendered UI text if the redirect does not occur

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-763/test_ts_763.py
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
Pass: the direct dashboard URL is intercepted, startup completes, and the user
lands on Project Settings instead of the dashboard shell.

Fail: the app stays on the dashboard route, renders dashboard content, remains
on the splash screen, or otherwise does not expose the Project Settings landing
screen for an empty-workspace browser context.
```

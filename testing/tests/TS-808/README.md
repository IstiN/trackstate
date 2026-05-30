# TS-808 test automation

Verifies that the live desktop TrackState workspace switcher hides the
**Connect GitHub** control for the currently active local workspace when the
user is already signed in to GitHub. The setup switches to the prepared local
workspace and preloads the workspace-scoped GitHub session state the live app
uses for the local-row access check before falling back to the visible connect
flow during setup.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-808/test_ts_808.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the active local workspace row stays in the Local Git state and does not
show Connect GitHub in that row's visible text or row-owned controls while the
session is already authenticated.

Fail: the active local row still exposes Connect GitHub as a visible action,
button, or row label while signed in.
```

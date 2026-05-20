# TS-833 test automation

Verifies that pressing `ArrowDown` in the live desktop TrackState workspace
switcher moves the active saved-workspace selection to the next workspace while
keeping the panel open.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
   and two preloaded saved hosted workspaces
2. opens the desktop workspace switcher from Dashboard
3. observes the currently selected saved workspace row before any keyboard input
4. clicks the active saved-workspace row to engage keyboard interaction on the
   open switcher before sending `ArrowDown`
5. checks whether the active saved workspace changes from `Hosted main
   workspace` to `Hosted alt workspace` while the panel remains visible

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-833/test_ts_833.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: on desktop, pressing ArrowDown in the open workspace switcher keeps the
panel visible and moves the active saved workspace from Hosted main workspace
to Hosted alt workspace.

Fail: ArrowDown dismisses the panel, the panel visibly flashes closed, or the
active saved workspace does not move to the next visible workspace row.
```

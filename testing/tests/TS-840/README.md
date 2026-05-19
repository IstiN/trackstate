# TS-840 test automation

Verifies that clicking a saved workspace row in the live desktop TrackState
workspace switcher moves keyboard focus onto that row so Arrow Down navigation
is handled by the switcher instead of the global view.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
   and two preloaded saved hosted workspaces
2. opens the desktop workspace switcher from Dashboard
3. clicks the active saved-workspace row and confirms the focused element is the
   clicked row button inside the open switcher
4. presses `ArrowDown` and waits for the active saved workspace to change to the
   next visible row while the panel stays open

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-840/test_ts_840.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: clicking the active saved workspace row focuses that row inside the open
workspace switcher, and ArrowDown moves the active selection from Hosted main
workspace to Hosted alt workspace while the panel remains visible.

Fail: clicking the row leaves focus on the global view or trigger, or ArrowDown
does not move the active selection to the next visible saved workspace row.
```

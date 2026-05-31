# TS-842 test automation

Verifies that pressing `ArrowDown` while the last saved workspace row is selected
in the live desktop TrackState workspace switcher keeps the selection within list
boundaries and does not lose keyboard focus to the global view.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
   and two preloaded saved hosted workspaces
2. opens the desktop workspace switcher from Dashboard
3. focuses the active saved-workspace row and advances selection until the last
    saved workspace is highlighted
4. explicitly restores keyboard focus onto the selected last saved-workspace row
   before pressing `ArrowDown`
5. presses `ArrowDown` on the last saved workspace row across several fresh live
   trials to confirm the boundary behavior remains stable

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-842/test_ts_842.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: from the last saved workspace row, pressing ArrowDown leaves the workspace
switcher visibly open, keeps the active selection on the last row or wraps it to
the first row, and keeps keyboard focus inside the open switcher.

Fail: the panel closes, no saved workspace remains active, the active selection
leaves the visible list, or keyboard focus escapes to the global page view.
```

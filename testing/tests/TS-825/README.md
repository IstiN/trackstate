# TS-825 test automation

Verifies that the live desktop TrackState workspace switcher stays open when the
user presses non-Escape navigation keys inside the panel.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
   and two preloaded saved hosted workspaces
2. opens the desktop workspace switcher from Dashboard
3. starts `ArrowDown` from the visible saved-workspace surface so the key path
   targets the actual workspace list instead of the add-workspace form
4. checks whether `ArrowDown` moves the active saved workspace to another row
   while the panel remains open
5. exercises `Shift` and `Tab` while the panel is open, using the `Repository`
   field only for the separate in-panel Tab focus traversal

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-825/test_ts_825.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: on desktop, the workspace switcher remains visibly open after ArrowDown,
Shift, and Tab; ArrowDown moves the active saved workspace to another visible
row; and Tab keeps keyboard focus inside the panel instead of dismissing it.

Fail: any of those keys dismisses the panel, the panel visibly flashes closed,
ArrowDown does not move the active saved workspace to another visible row, or
Tab leaves the panel instead of moving to another visible in-panel control.
```

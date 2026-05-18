# TS-834 test automation

Verifies that pressing `ArrowDown` inside the live desktop TrackState workspace
switcher does not scroll the background page.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
 and two preloaded saved hosted workspaces
2. navigates to Settings, where the live background surface is scrollable
3. resizes to a desktop viewport and scrolls the Settings background surface to a non-zero vertical position
4. opens the desktop workspace switcher from Settings
5. tabs to a real visible in-panel button and verifies the open switcher still
   owns keyboard focus before sending `ArrowDown`
6. checks whether `ArrowDown` moves the active saved workspace to another row
   while keeping the background page at the same scroll position

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-834/test_ts_834.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: on desktop, ArrowDown changes the active saved workspace from the current
row to the next visible saved workspace row while the background page remains at
the same vertical scroll position.

Fail: ArrowDown dismisses the panel, does not move the active saved workspace to
another visible row, or changes the background page scroll position.
```

# TS-722 test automation

Verifies that the live TrackState app shell replaces the legacy repository-access
button with a workspace switcher across tracker sections, keeps the active
workspace name/icon/state visible on desktop, opens the desktop surface, and
adapts the trigger and container for a compact/mobile layout.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
PYTHONPATH=. python3 testing/tests/TS-722/test_ts_722.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the workspace switcher replaces the legacy repository-access button in
Dashboard, Board, JQL Search, and Settings; the desktop trigger keeps the
active workspace name, icon, and state badge; opening it yields a desktop
dialog surface; and the compact layout keeps an icon-led trigger plus a bottom
sheet or full-screen sheet.

Fail: any tracker section still exposes the legacy control, the trigger loses
the workspace name/icon/state, the desktop surface opens in the wrong
container/layout, or the compact view fails to present the expected mobile
trigger and sheet behavior.
```

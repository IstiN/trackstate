# TS-798 test automation

Verifies that the live desktop workspace switcher opens as a non-modal desktop
surface without background dimming and that the visible desktop header remains
interactive while the switcher is open by probing another visible top-bar
control such as the theme toggle.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
PYTHONPATH=. python3 testing/tests/TS-798/test_ts_798.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: on desktop, opening the workspace switcher does not dim the background or
behave like a modal overlay, and the user can still interact with another header
control such as the theme toggle.

Fail: opening the switcher dims the background, behaves like a modal dialog, or
blocks interaction with the visible desktop header controls.
```

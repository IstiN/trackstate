# TS-859 test automation

Verifies that pressing `Space` on a keyboard-focused in-panel control inside the
live desktop TrackState workspace switcher does not bubble into the trigger's
toggle-close logic.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
   and deterministic saved workspace profiles
2. reaches the workspace switcher trigger through real keyboard navigation and
   opens the surface with `Space`
3. uses keyboard `Tab` navigation to focus the in-panel `Branch` field
4. presses `Space` on that focused field and asserts the field value changes
   while the workspace switcher stays open and the selected workspace does not
   change

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-859/test_ts_859.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: keyboard Tab navigation reaches the visible Branch field, pressing Space
changes that field's value, the workspace switcher stays open, focus remains on
the Branch field, and the active workspace stays on Hosted main workspace.

Fail: keyboard focus never reaches the Branch field, Space does not change the
field value, the panel closes, focus jumps back to the trigger, or the active
workspace changes.
```

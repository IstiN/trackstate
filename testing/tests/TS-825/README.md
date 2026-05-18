# TS-825 test automation

Verifies that the live desktop TrackState workspace switcher stays open when the
user presses non-Escape navigation keys inside the panel.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
2. opens the desktop workspace switcher from Dashboard
3. focuses the visible `Repository` field inside the panel to exercise in-panel
   keyboard handling instead of the blur-to-dismiss path already covered by
   TS-821
4. presses `ArrowDown` and `Shift` while the panel is open and confirms the
   visible panel does not dismiss
5. presses `Tab` from the `Repository` field, confirms focus moves to another
   visible control inside the panel, and confirms the panel still does not
   dismiss

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
Shift, and Tab, and Tab keeps keyboard focus inside the panel instead of
dismissing it.

Fail: any of those keys dismisses the panel, the panel visibly flashes closed,
or Tab leaves the panel instead of moving to another visible in-panel control.
```

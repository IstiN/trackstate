# TS-821

Verifies that the live desktop TrackState workspace switcher dismisses when it
loses focus via keyboard navigation.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
2. opens the desktop workspace switcher from Dashboard
3. presses `Tab` once and verifies focus leaves the switcher for another visible
   in-viewport interactive control outside the component
4. waits up to 6 seconds for the panel to dismiss after blur before asserting
5. records the focused target, visible panel text, and screenshot for failure
   triage if the switcher remains open

The live run uses the default desktop viewport of `1440x900`.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-821/test_ts_821.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: after the desktop workspace switcher is opened, pressing Tab moves focus
to a different visible in-viewport interactive element outside the switcher and
the panel closes automatically within the wait window.

Fail: focus does not leave the switcher, or it leaves the switcher but the panel
remains visible instead of dismissing on blur.
```

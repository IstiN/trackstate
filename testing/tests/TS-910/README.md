# TS-910

Verifies that desktop keyboard Tab navigation stays trapped inside the open
workspace switcher and wraps from the last visible panel control back to the
first interactive element inside the panel.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
   and a preloaded set of hosted workspace profiles at the default desktop
   viewport of 1440x900
2. opens the desktop workspace switcher and confirms the visible panel renders
   the workspace rows plus the footer controls
3. moves keyboard focus to the selected first saved workspace row inside the
   panel
4. presses `Tab` until the visible footer `Save and switch` button is reached
   while confirming focus never escapes the open switcher
5. presses `Tab` once more and verifies focus wraps back to the first saved
   workspace row instead of remaining on the footer button or escaping to
   external controls

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-910/test_ts_910.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: after keyboard focus advances through the interactive controls inside the
open desktop workspace switcher, pressing Tab on the last visible panel control
wraps focus back to the first saved workspace row without leaving the panel.
```

# TS-1008

Validates that clicking the disabled `Save and switch` footer control in a
pristine live desktop workspace switcher does not collapse the open panel.

The automation:
1. preloads hosted workspace profiles without changing the active workspace
2. opens the deployed TrackState app at the required desktop viewport
3. verifies the visible footer renders `Save and switch` in a disabled state
4. clicks that disabled footer control with a real pointer action and checks the
   workspace switcher stays visibly open

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1008/test_ts_1008.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

The workspace switcher remains open after the disabled `Save and switch` button
is clicked, and the footer button continues to report its disabled state.

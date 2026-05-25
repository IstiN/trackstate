# TS-954

Validates that the live desktop workspace switcher still renders the footer
`Save and switch` control in a pristine state, marks it disabled, and keeps it
in the keyboard focus loop so focus wraps back to the first saved workspace row.

The automation:
1. preloads hosted workspace profiles without making any workspace changes
2. opens the deployed TrackState app at the desktop default viewport
3. opens the workspace switcher and checks the visible footer
4. verifies `Save and switch` is visible, disabled, tabbable, and still serves
   as the wrap boundary for the focus trap

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-954/test_ts_954.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- defaults come from `testing/core/config/live_setup_test_config.py`

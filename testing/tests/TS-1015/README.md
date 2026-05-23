# TS-1015

Validates that clicking the current inert workspace row inside the live desktop
workspace switcher does not collapse the panel.

The automation:
1. preloads hosted workspace profiles with a current active workspace
2. opens the deployed TrackState app at the required desktop viewport
3. verifies the current workspace entry is rendered as the selected `Active` row
4. clicks that row with a real pointer action and checks the switcher stays open

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1015/test_ts_1015.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

The workspace switcher remains open after the current inert workspace row is
clicked, and the selected row stays visible instead of collapsing the panel.

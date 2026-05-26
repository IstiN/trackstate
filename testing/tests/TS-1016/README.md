# TS-1016

Validates that clicking a disabled interactive element outside the live desktop
workspace switcher is treated as an external interaction and immediately closes
the open panel.

The automation:
1. preloads hosted workspace profiles without changing the active workspace
2. opens the deployed TrackState app in Chromium at `1440x900`
3. verifies a visible disabled interactive background control exists outside the
   switcher DOM and panel bounds
4. clicks that disabled control with a real pointer action and confirms the
   workspace switcher closes while the dashboard shell remains visible

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1016/test_ts_1016.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

The workspace switcher closes immediately after the real pointer click lands on
the disabled background control, and the dashboard shell remains visible.

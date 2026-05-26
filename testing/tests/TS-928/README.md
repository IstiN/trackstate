# TS-928

Validates that the live workspace switcher renders the visible `Delete` action
with WCAG AA text contrast after the TS-902 accessibility fix.

The automation:
1. opens the deployed TrackState web app in Chromium with preloaded saved
   workspace profiles
2. runs the scenario at the desktop viewport of `1440x900`
3. opens the live **Workspace switcher**
4. identifies the visible `Delete` action for the hosted workspace row (prefers
   `Delete: istin/trackstate-setup` when present)
5. measures the rendered `Delete` text contrast against the workspace switcher
   surface background and records the paired icon colors as diagnostics

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-928/test_ts_928.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the deployed workspace switcher shows a visible Delete action in the saved
workspace list, and that Delete text measures at least 4.5:1 contrast against
the rendered switcher surface background.
```

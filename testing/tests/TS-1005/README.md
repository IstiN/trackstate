# TS-1005

Validates that startup clears the active selection and returns the user to the
default landing state when the previously active local workspace resolves to
`Unavailable` during hydration.

The automation:
1. preloads a broken saved local workspace as the active startup target plus one
   hosted fallback workspace in browser storage
2. opens the deployed TrackState app in Chromium at `1440x900`
3. waits for startup hydration to settle, then verifies the current visible view
   is not the dashboard and records the live URL
4. opens **Workspace switcher** and verifies the broken local workspace is shown
   as `Unavailable` without still being selected or labeled `Active`

Linked regression context covered by this automation: `TS-1011`, `TS-995`.
## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1005/test_ts_1005.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: startup does not leave the user on the dashboard for the broken saved
workspace. The app falls back to the default landing surface, and Workspace
switcher shows the broken local workspace as Unavailable without any Active
selection.

Fail: startup still loads the dashboard for the broken workspace, Workspace
switcher cannot be opened, or the broken local workspace remains selected /
Active even after it resolves to Unavailable.
```

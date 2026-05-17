# TS-759

Validates that startup recovery stays on the visible **Project Settings**
recovery screen when the user retries without fixing the saved invalid
workspace configuration.

The automation:
1. opens the deployed TrackState app in Chromium with invalid saved workspaces
   preloaded in browser storage
2. waits for the Settings / startup recovery shell to appear
3. clicks **Retry** without correcting the workspace configuration
4. waits for startup validation to run again against the invalid hosted branch
5. verifies the app remains on the recovery screen with **Retry** still visible

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-759/test_ts_759.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`
- Optional overrides:
  - `TRACKSTATE_LIVE_APP_URL`
  - `TRACKSTATE_LIVE_SETUP_REPOSITORY`
  - `TRACKSTATE_LIVE_SETUP_REF`

## Expected result

```text
Pass: startup reaches the Settings / startup recovery shell, Retry triggers a
fresh validation attempt against the still-invalid saved workspaces, and the UI
remains on the recovery screen with Retry still available.

Fail: startup never reaches the recovery shell, Retry is unavailable, Retry does
not trigger another validation attempt, or the app leaves the recovery screen
even though the saved workspaces are still invalid.
```

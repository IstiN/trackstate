# TS-758

Validates that the startup recovery **Retry** action re-validates a saved
workspace after that workspace becomes valid and then opens the live tracker
interface instead of leaving the user stranded on the recovery screen.

The automation:
1. preloads one saved hosted workspace that initially fails validation because
   its branch does not exist in the live GitHub repository
2. launches the deployed TrackState app and waits for the Settings / startup
   recovery shell to appear
3. changes the same saved workspace to a valid state by creating that exact
   saved branch in the live GitHub repository from the configured source ref
4. clicks **Retry**
5. verifies the app re-validates that saved workspace, opens the interactive
   tracker shell, keeps that saved workspace active in browser storage, and
   dismisses startup recovery

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-758/test_ts_758.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: startup lands on the Settings / startup recovery screen while the saved
workspace is invalid, Retry re-runs validation after the workspace becomes
valid, restores that same saved workspace as active, and opens the live
tracker shell.

Fail: startup never reaches recovery, Retry never re-validates the saved
workspace, or the app stays on recovery / a broken state instead of loading the
tracker shell.
```

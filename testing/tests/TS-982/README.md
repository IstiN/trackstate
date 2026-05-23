# TS-982

Validates that a non-200 workspace-sync bootstrap response does not block the
deployed desktop shell.

The automation:
1. seeds a hosted workspace and stored GitHub token into browser storage
2. injects a one-time `500 Internal Server Error` on the second repository
   metadata request so the startup workspace-sync path fails after initial data
   hydration begins
3. waits for the visible failure message instead of asserting immediately
4. verifies the shell still exposes the desktop navigation and workspace
   switcher trigger
5. opens the workspace switcher and confirms the saved hosted workspace remains
   available in a visible fallback state rather than leaving the app stuck on a
   terminal error surface

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-982/test_ts_982.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the one-time 500 error surfaces as a visible startup-sync failure while
the desktop shell stays interactive, the top bar and sidebar remain available,
and Workspace switcher still opens with the hosted workspace shown in a visible
fallback state.

Fail: startup collapses to a blank or terminal error surface, the desktop shell
never becomes interactive, or Workspace switcher cannot expose the saved hosted
workspace after the synthetic 500 failure.
```

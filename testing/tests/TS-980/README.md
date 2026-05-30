# TS-980

Validates that a saved local workspace which has already been manually restored
to `Local Git` stays in `Local Git` after the app is refreshed.

The automation:
1. preloads one hosted workspace as active plus one saved local workspace in the
   `Unavailable` state
2. recreates the local repository on disk so the saved workspace becomes
   restorable
3. uses the visible Retry/Re-authenticate action to restore the workspace and
   waits for a real browser directory-access callback plus the active `Local Git`
   state
4. performs a hard reload of the deployed app
5. verifies the same workspace remains active as `Local Git` and still shows the
   expected branch details in the Workspace switcher

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-980/test_ts_980.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the saved unavailable local workspace restores to Local Git, a hard reload
does not revert it, and the Workspace switcher still shows the same Local Git
workspace with its branch details.

Fail: the restore precondition cannot be established, the hard reload reverts
the workspace away from Local Git, or the Workspace switcher no longer shows the
expected Local Git status and branch details.
```

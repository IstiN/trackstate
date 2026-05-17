# TS-727

Validates that startup recovery routes the user to **Project Settings** when all
previously saved workspaces are invalid.

The automation:
1. opens the deployed TrackState app in Chromium with two invalid saved
   workspaces preloaded in browser storage
2. uses one invalid Local path and one Hosted repository branch that does not
   exist
3. waits for the startup restoration flow to validate the saved candidates
4. verifies the user-visible fallback lands on the Settings / startup recovery
   shell instead of leaving the app stuck in a broken startup state
5. records screenshots and observed GitHub requests as failure evidence when the
   recovery screen does not appear

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-727/test_ts_727.py
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
Pass: startup attempts to restore the saved workspaces, determines that every
candidate is invalid, and automatically routes the user to the Settings /
startup recovery shell with visible recovery actions.

Fail: startup remains stuck on the splash screen, reaches a broken tracker
state, or never exposes the Settings / startup recovery surface after the saved
workspace validation flow completes.
```

# TS-1006

Validates that a directory mismatch on an inactive saved workspace does not clear
the active valid workspace during startup hydration.

The automation:
1. opens the deployed TrackState web app in Chromium at `1440x900`
2. establishes **Workspace A** as a real saved local workspace through the
   visible `Retry` / `Re-authenticate` recovery action
3. updates the persisted workspace state so startup begins with exactly two saved
   local workspaces: **Workspace A** (active and valid) and **Workspace B**
   (inactive and broken)
4. reloads the app and waits for startup hydration to settle before asserting
5. verifies the header and dashboard still show **Workspace A** as active
6. opens **Workspace switcher** and checks that **Workspace A** stays active
   while **Workspace B** is shown as `Unavailable` and not `Active`

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1006/test_ts_1006.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: after startup hydration completes, Workspace A remains the active Local Git
workspace, the dashboard shell stays visible, and Workspace B is shown as
Unavailable without taking over the Active selection.

Fail: the app cannot hold Workspace A as the active Local Git workspace through
the setup/startup flow, startup drops back to a non-local workspace or landing
surface, or Workspace B still clears/takes the Active selection during startup.
```


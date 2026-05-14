# TS-725

Verifies the deployed workspace switcher keeps inactive hosted rows deterministic
while still showing the live Local Git state for the active local workspace.

The automation:
1. preloads browser storage with one active local workspace and one inactive
   hosted workspace while signed out
2. opens the deployed TrackState app in Chromium
3. opens **Workspace switcher** and checks the active local row shows `Local Git`
4. checks the inactive hosted row shows `Needs sign-in` and does not show
   `Connected` or `Read-only`
5. signs in to GitHub through the live app from the active local workspace
6. reopens **Workspace switcher** and verifies the inactive hosted row still
   shows the deterministic non-live state instead of a misleading live access
   state

## Install dependencies

```bash
python3 -m pip install --user playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-725/test_ts_725.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the active local workspace row shows Local Git, and the inactive hosted
workspace row shows Needs sign-in both before and after signing in from the
active local workspace. The inactive hosted row never upgrades to Connected or
Read-only until it becomes active or is explicitly validated.
```


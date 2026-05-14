# TS-725

Verifies the deployed workspace switcher keeps inactive hosted rows deterministic
while using a supported active hosted workspace runtime for the live sign-in flow.

The automation:
1. preloads browser storage with one active hosted workspace and one inactive
   hosted workspace while signed out
2. opens the deployed TrackState app in Chromium
3. opens **Workspace switcher** and checks the active hosted row shows
   `Needs sign-in`
4. checks the inactive hosted row shows `Needs sign-in` and does not show
   a live hosted access state
5. signs in to GitHub through the live app from the active hosted workspace
6. reopens **Workspace switcher** and verifies the inactive hosted row still
   shows the deterministic non-live state while the active hosted row upgrades
   to the live connected state for that workspace

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
Pass: the active hosted workspace row starts at Needs sign-in and upgrades to a
live hosted access state after signing in, while the inactive hosted workspace
row stays at Needs sign-in and does not recalculate live access.
```

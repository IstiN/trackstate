# TS-818 test automation

Verifies that the live desktop TrackState workspace switcher does not expose an
incorrect workspace state during startup hydration when an active local
workspace is already configured.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-818/test_ts_818.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: after reloading the deployed app and attempting to open Workspace
switcher immediately, the user never sees an incorrect hydration state such as
Hosted / Needs sign-in or Local Unavailable, and the flow settles to the active
local workspace in the Local Git state.

Fail: the user can see an incorrect workspace state during hydration, or the
flow never settles to the active local Local Git state within the observation
window.
```

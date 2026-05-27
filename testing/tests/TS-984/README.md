# TS-984

Verifies the deployed TrackState shell becomes visible through the explicit
11-second startup timeout path even when the initial GitHub `/user` probe is
artificially delayed past 30 seconds.

The automation:
1. opens the hosted TrackState app in Chromium with a stored GitHub token
2. preloads a hosted saved workspace profile for the live setup repository
3. delays the initial GitHub `/user` startup probe for 31 seconds inside the browser runtime
4. waits until 11 seconds have elapsed from application launch
5. checks for a user-visible TopBar workspace trigger and visible branding text
   while the delayed probe is still pending
6. writes the required result artifacts to `outputs/`

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-984/test_ts_984.py
```

## Required environment / config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected passing output

```text
TS-984 passed
```

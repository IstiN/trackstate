# TS-990

Validates that the deployed TrackState app keeps the visible shell stable after
the delayed startup synchronization probe times out and later resolves.

The automation:
1. preloads a signed-in browser state with both local and hosted workspace
   profiles for the deployed app
2. delays the initial GitHub `/user` startup probe by 30 seconds so the probe
   remains pending beyond the 11-second synchronization window in the live
   deployment, even though the request itself starts several seconds after app
   launch
3. waits past the timeout before asserting so the linked TS-971 non-blocking
   shell-ready behavior is exercised
4. keeps sampling the real deployed shell until the delayed probe resolves and
   checks that navigation, the workspace trigger, route, and TrackState branding
   stay stable from the user's perspective
5. records a real failed product bug if the late probe resolution causes a UI
   reset, flicker, or duplicate visible state change

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-990/test_ts_990.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to `https://istin.github.io/trackstate-setup/` and GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected output when the test passes

```text
TS-990 passed
```

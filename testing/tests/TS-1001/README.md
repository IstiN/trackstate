# TS-1001

Validates that the deployed TrackState app applies the restricted fallback
session after the 11-second startup timeout when the GitHub `/user` auth probe
is still hanging.

The automation:
1. preloads a hosted workspace and stored GitHub token into the live app
2. delays the initial GitHub `/user` startup probe by 30 seconds so the auth
   request should still be unresolved after the 11-second timeout window
3. waits past the timeout before asserting
4. verifies the shell is visible, the hosted workspace shows the exact
   `Needs sign-in` fallback state, and write actions are blocked by the user
   facing `Open settings` gate
5. records a real product failure if the delayed auth probe never starts, the
   shell does not become interactive, or the write-capability gate is missing

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1001/test_ts_1001.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to `https://istin.github.io/trackstate-setup/` and GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected output when the test passes

```text
TS-1001 passed
```

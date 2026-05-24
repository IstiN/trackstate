# TS-1001

Validates that the deployed TrackState app applies the restricted fallback
session after the 11-second startup timeout when the GitHub `/user` auth probe
is still hanging.

The automation:
1. preloads the hosted workspace plus a stored GitHub token into the live app
2. keeps the GitHub `/user` auth probe delayed in the browser runtime so auth
   stays unresolved if the deployed app starts it during the run
3. waits past the timeout before asserting the visible hosted fallback shell
4. verifies the exact `Needs sign-in` trigger state and the user-facing
   `Open settings` Create issue recovery gate on the deployed app
5. runs a production Dart provider probe that delays `/user` for 30 seconds and
   verifies `canWrite == false` and `canCreateBranch == false` at the delayed-auth checkpoint

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
- Dart 3.9+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to `https://istin.github.io/trackstate-setup/` and GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected output when the test passes

```text
TS-1001 passed
```

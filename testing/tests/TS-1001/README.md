# TS-1001

Validates that the deployed TrackState app applies the restricted fallback
session after the 11-second startup timeout when the GitHub `/user` auth probe
is still hanging.

The automation:
1. preloads local and hosted workspaces plus a stored GitHub token into the live app
2. starts from the active hosted workspace so the initial GitHub `/user` startup
   probe is exercised deterministically, then delays that probe by 30 seconds so
   auth stays unresolved after the 11-second timeout window
3. waits past the timeout before asserting
4. verifies the exact `Needs sign-in` fallback state on the active hosted
   workspace plus the user-facing `Open settings` write gate
5. reads the hosted workspace access mode from the same live browser session to
   confirm the fallback stayed in the disconnected hosted state
6. records a real product failure when the live app still does not expose any
   public same-session surface for proving `canCreateBranch == false`

Linked startup fixes reviewed for timing and gating behavior: TS-1022,
TS-1014, TS-1013, TS-1012, TS-996, and TS-992.

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

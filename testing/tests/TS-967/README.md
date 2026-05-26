# TS-967

Validates that the deployed TrackState app uses a non-blocking startup pattern
for synchronization initialization, so the interactive shell becomes available
even while the initial GitHub `/user` probe is still delayed beyond the explicit
timeout window.

The automation:
1. preloads a signed-in browser state with both local and hosted workspace
   profiles for the deployed app
2. delays the initial GitHub `/user` startup probe by 30 seconds to keep sync
   initialization pending past the 10-second timeout
3. waits past the timeout window before asserting so the check observes the
   fixed async behavior instead of checking too early
4. verifies the live page exposes shell navigation, the header workspace
   trigger, and TrackState branding instead of remaining on the startup
   surface
5. records a real failed product bug if the shell only becomes available after
   the delayed probe is released

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-967/test_ts_967.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to `https://istin.github.io/trackstate-setup/` and GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected output when the test passes

```text
TS-967 passed
```

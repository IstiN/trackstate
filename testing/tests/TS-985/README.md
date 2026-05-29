# TS-985

Validates that the deployed TrackState app reaches the interactive shell as soon
as a short successful startup probe completes, instead of waiting for the full
synchronization timeout window.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored GitHub token
   and preloaded workspace state
2. delays the initial GitHub `/user` startup probe by 2 seconds so the startup
   success path remains observable
3. waits for the live shell to report `shell_ready`
4. verifies the visible shell appears shortly after the delayed probe is
   released and before the full 11-second timeout window
5. confirms the visible surface contains interactive shell navigation, the
   header workspace trigger, and TrackState branding from a user perspective

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-985/test_ts_985.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to `https://istin.github.io/trackstate-setup/` and GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected output when the test passes

```text
TS-985 passed
```

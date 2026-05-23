# TS-1019

Validates that the deployed TrackState app keeps the startup shell hidden while
the delayed GitHub `/user` startup probe is still pending, then renders the
interactive shell only after that probe resolves.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored GitHub token
   and preloaded workspace state
2. delays the initial GitHub `/user` startup probe by 5 seconds so the pending
   startup window is long enough to inspect reliably
3. samples the live page throughout that pending window instead of asserting
   immediately
4. verifies the TopBar trigger, sidebar navigation, and branding stay hidden and
   absent from the shell DOM markers while the probe is pending
5. confirms the real deployed shell becomes interactive after the probe
   is released

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1019/test_ts_1019.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to `https://istin.github.io/trackstate-setup/` and GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected output when the test passes

```text
TS-1019 passed
```

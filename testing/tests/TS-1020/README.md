# TS-1020

Validates that the deployed TrackState startup state machine does not enter the
interactive shell before its delayed startup guard resolves.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored GitHub token
   and preloaded workspace state
2. delays the initial GitHub `/user` startup probe by 5 seconds so the guarded
   startup window stays observable
3. confirms the live app does not report `shell_ready` while that delayed probe
   is still pending
4. verifies the shell becomes interactive only after the probe succeeds, with
   visible navigation, the top-bar workspace trigger, and TrackState branding

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1020/test_ts_1020.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to `https://istin.github.io/trackstate-setup/` and GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the delayed startup guard keeps the app out of the interactive shell while
the probe is pending, and the live shell becomes interactive only after that
probe succeeds.

Fail: shell_ready becomes visible before the delayed startup probe resolves, the
app never reaches the interactive shell after probe success, or the final page
does not expose the expected user-visible shell navigation and branding.
```

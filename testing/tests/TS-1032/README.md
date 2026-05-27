# TS-1032

Validates the deployed TrackState startup sequence with a validator utility that
confirms the live startup path can reach the bootstrap, pending, and resolved
phases in order.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored GitHub token
   and preloaded local plus hosted workspace state
2. delays the initial GitHub `/user` startup probe by 5 seconds so the pending
   phase stays observable long enough for live validation
3. samples the live startup window and runs a validator utility against the
   observed initialization logic map
4. confirms the startup path reaches bootstrap, pending, and resolved, then
   verifies the real user-visible shell appears only after resolution

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1032/test_ts_1032.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to `https://istin.github.io/trackstate-setup/` and GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

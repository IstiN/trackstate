# TS-921

Validates manual re-authentication for an unavailable local workspace when the
browser directory picker returns a different directory than the saved workspace
expects.

The automation:
1. preloads one hosted workspace plus one saved local workspace that should be
   unavailable
2. opens the deployed Workspace switcher and looks for the unavailable local
   workspace row a user would retry
3. forces the browser directory picker callback to return a different directory
4. verifies the app surfaces a visible failure and keeps the workspace out of
   the `Local Git` state

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-921/test_ts_921.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- defaults come from `testing/core/config/live_setup_test_config.py`

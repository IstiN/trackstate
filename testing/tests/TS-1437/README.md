# TS-1437

Verifies the Connect GitHub button in hosted Project Settings is clickable and
opens the GitHub connection dialog.

## Run this test

```bash
python testing/tests/TS-1437/test_ts_1437.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Scenario notes

The test opens the deployed hosted app with a stored hosted-workspace token,
navigates to Project Settings, and clicks the Connect GitHub button. A passing
result means the button click succeeds within the timeout and the Connect GitHub
dialog renders with the Fine-grained token field.
# TS-525 test automation

Validates that the hosted **Attachments** tab stays download-only when the
session resolves `canUpload = false`.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-525/test_ts_525.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Scenario notes

- The test seeds the live hosted `DEMO-2` issue with a repository-path
  attachment so the Attachments tab always has an existing download row.
- It patches the hosted repository permission response to read-only so the live
  session resolves `canUpload = false` without changing production code.
- A passing result means the hosted **Attachments** tab keeps the existing
  download action reachable while exposing no visible or keyboard-reachable
  upload or replacement controls.

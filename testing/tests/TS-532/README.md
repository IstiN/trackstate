# TS-532 test automation

Validates that the hosted **Attachments** tab recovery action navigates from the
repository-path restriction notice to **Project Settings** with the
**Attachments** sub-tab selected.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-532/test_ts_532.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Scenario notes

- The test opens the live hosted `DEMO-2` issue in the deployed app.
- It temporarily switches `DEMO/project.json` to
  `attachmentStorage.mode = repository-path` when the live setup repo is in a
  different storage mode, then restores the original file after the run.
- A passing result means the repository-path browser notice exposes
  `Open settings`, activating it lands on **Project Settings > Attachments**,
  and the `Attachment storage mode` configuration is visible.

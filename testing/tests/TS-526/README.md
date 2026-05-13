# TS-526 test automation

Validates the hosted **Attachments** tab behavior when the live project is in
`repository-path` attachment storage mode.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-526/test_ts_526.py
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
- A passing result means the hosted **Attachments** tab shows the repository-path
  browser restriction notice, keeps existing download rows visible, and does not
  render visible `Choose attachment` or `Upload attachment` controls.

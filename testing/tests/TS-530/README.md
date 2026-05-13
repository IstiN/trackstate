# TS-530 test automation

Verifies that the hosted **Attachments** tab shows the repository-path browser
restriction notice, keeps existing downloads visible, hides browser upload
controls, and exposes a usable **Open settings** recovery action.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-530/test_ts_530.py
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
- A passing result means the repository-path browser notice is visible at the
  top of the hosted **Attachments** tab, existing attachments remain available
  for download below it, browser upload controls stay hidden, and `Open
  settings` lands on **Project Settings > Attachments** with `Attachment
  storage mode` visible.

# TS-531 test automation

Verifies the hosted **Attachments** tab behavior for the ticket's `default`
attachment-storage precondition.

The automation:
1. opens the live hosted `DEMO-2` issue in the deployed app
2. temporarily removes `DEMO/project.json` `attachmentStorage` so the live setup
   repo uses the product's default attachment path, then restores the original
   file after the run
3. checks whether the hosted **Attachments** tab hides restriction UI and keeps
   visible `Choose attachment` / `Upload attachment` controls
4. if the default path still resolves to the repository-path download-only
   state, reports that as the real product-visible gap instead of pretending
   the standard hosted upload contract was verified

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-531/test_ts_531.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected pass / fail behavior

- **Pass:** the hosted default attachment path shows no restriction notice or
  `Open settings` action, visible `Choose attachment` and `Upload attachment`
  controls remain interactive, and selecting a file enables upload.
- **Fail:** the hosted default path still falls into the repository-path or
  other restricted flow, shows storage restriction UI, hides upload controls,
  or otherwise cannot expose the standard browser upload surface required by
  the ticket.

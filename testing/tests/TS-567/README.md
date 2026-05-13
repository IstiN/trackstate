# TS-567 test automation

Validates that the hosted **Attachments** flow surfaces a visible runtime error
instead of a false success state when an upload is attempted after the active
attachment provider becomes unavailable or unsupported.

The automation:
1. opens the live hosted `DEMO-2` issue in the deployed app
2. verifies the `Attachments` tab exposes the hosted browser upload controls
3. selects a real file through the hosted chooser and confirms the selected-file
   summary is visible before upload
4. injects a ticket-scoped runtime fault that removes the hosted repository
   permission payload needed to keep the release-backed provider initialized
5. clicks `Upload attachment` and checks for the exact visible `Save failed`
   message instead of a completed attachment row

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-567/test_ts_567.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected pass / fail behavior

```text
Pass: the hosted Attachments tab reaches the pre-upload state, the synthetic
provider fault is exercised on upload, the page shows the exact visible
"Save failed" error, and the selected file never appears as a completed
attachment.

Fail: the hosted app no longer exposes upload controls, the selected-file state
never appears, the provider fault is not exercised, the visible error text does
not appear, or the UI still renders the upload as completed.
```

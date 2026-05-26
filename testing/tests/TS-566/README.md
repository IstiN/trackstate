# TS-566 test automation

Validates that the hosted **Attachments** flow completes a real
`github-releases` upload and persists the required repository-visible
postconditions.

The automation:
1. opens the live hosted `DEMO-2` issue in the deployed app
2. switches the project to `attachmentStorage.mode = github-releases` with a
   unique release tag prefix for the run
3. chooses and submits a real file from the hosted **Attachments** tab
4. waits for the uploaded file to appear as a visible attachment row
5. verifies the corresponding GitHub Release asset and `attachments.json`
   metadata through the repository API

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && python testing/tests/TS-566/test_ts_566.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository with write access
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected pass / fail behavior

```text
Pass: the hosted Attachments tab exposes the upload controls, the selected file
can be submitted, the new attachment row appears, and exactly one matching
GitHub Release asset plus one matching attachments.json entry are created.

Fail: the hosted app does not expose the upload controls, the selected-file
state never appears, the UI never shows the uploaded attachment row, or the
release/manifest postconditions do not converge.
```

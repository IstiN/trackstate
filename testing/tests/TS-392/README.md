# TS-392 test automation

Verifies that the hosted **Attachments** tab shows a visible pre-upload summary
with the selected file name and file size before the upload is submitted.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-392/test_ts_392.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: opening Attachments, choosing a 2.5 MB file, and pausing before upload
shows a visible selected-file summary in the action area with the chosen file
name and size, while the file is still pending upload.

Fail: the pre-upload action area does not show the selected file name, does not
show the file size, places the summary in the wrong region, or only shows the
details after upload is submitted.
```

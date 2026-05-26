# TS-390 test automation

Verifies that the deployed hosted TrackState session blocks an LFS-tracked
attachment upload with specific local-Git guidance instead of a generic hosted
error.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-390/test_ts_390.py
```

## Required environment

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: The hosted Attachments tab keeps browser uploads enabled, choosing an
LFS-tracked file and clicking Upload shows a specific message that the file must
be added from a local Git runtime, and no live attachment write is attempted.

Fail: The hosted app shows only a generic error, misses the local-Git guidance,
or attempts to write the LFS-tracked attachment through the hosted session.
```

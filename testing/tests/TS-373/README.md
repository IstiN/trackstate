# TS-373 test automation

Verifies that the hosted **Attachments** area shows attachment-specific limited
upload messaging when Git LFS-style uploads are unavailable, while issue editing
and commenting remain enabled for the same authenticated session.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-373/test_ts_373.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the hosted issue detail view keeps edit and comment controls enabled, the
Attachments tab shows the "Some attachment uploads still require local Git"
callout, and the visible messaging stays limited to attachment upload
restrictions instead of implying repository-wide read-only access.

Fail: edit or comment controls are unavailable for the write-capable session,
the Attachments tab does not show the granular upload restriction message, or
the UI falls back to repository-wide read-only wording.
```

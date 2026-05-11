# TS-332 test automation

Verifies that the hosted **Attachments** collaboration tab exposes a keyboard-
reachable download control with a user-facing localized label for the seeded
attachment row.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-332/test_ts_332.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: The hosted Attachments tab shows the seeded attachment row, exposes a
visible "Download <filename>" control, keyboard Tab navigation can reach that
control from the Attachments tab, and pressing Enter starts the download.

Fail: The download control is missing, lacks the expected accessible label, is
not reachable with keyboard Tab navigation, or pressing Enter does not start the
download.
```

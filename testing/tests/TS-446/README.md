# TS-446 test automation

Verifies that the deployed hosted app does **not** trigger automatic bootstrap
retries after entering unauthenticated startup rate-limit recovery.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-446/test_ts_446.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- Defaults come from `testing/core/config/live_setup_test_config.py`
- Optional overrides:
  - `TRACKSTATE_LIVE_APP_URL`
  - `TRACKSTATE_LIVE_SETUP_REPOSITORY`
  - `TRACKSTATE_LIVE_SETUP_REF`
  - `TS446_RESULT_PATH`

## Expected result

```text
Pass: The deployed app enters unauthenticated rate-limit recovery, keeps the
visible Retry and Connect GitHub controls on screen, and makes no extra
bootstrap requests after network reconnect, focus regain, or the wait window.

Fail: Any of those events causes a new bootstrap request, the blocked endpoint
is retried before authentication, or the recovery view stops showing the user-
visible recovery controls.
```

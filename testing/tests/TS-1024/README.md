# TS-1024

Verifies that a consecutive retry failure keeps the deployed startup recovery UI
in a consistent `Sync issue` state and never exposes partial workspace rows or
footer controls.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1024/test_ts_1024.py
```

## Required environment and config

- Python 3
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Optional:
  - `TRACKSTATE_LIVE_APP_URL`
  - `TRACKSTATE_LIVE_SETUP_REPOSITORY`
  - `TRACKSTATE_LIVE_SETUP_REF`

## Test notes

- Reuses the live startup recovery page object and scopes recovery assertions to
  the recovery surface instead of document-wide text only.
- Samples the visible page state repeatedly for 5 seconds after the retry
  request is sent so async regressions still fail even if the UI only flickers
  into a partial-render state.

## Expected result

```text
Pass: clicking Retry sends another failing startup fetch, but the deployed app
stays in the recovery view. No saved workspace rows or Add workspace / Save and
switch footer controls become visible until a future successful sync occurs.
```

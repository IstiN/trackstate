# TS-983

Verifies that the startup recovery action re-triggers the blocked hosted
workspace fetch and, once the next request succeeds, the deployed app returns to
the interactive shell and exposes saved workspace rows plus footer controls in
the workspace switcher.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-983/test_ts_983.py
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

- Uses the startup recovery page object to find and click the recovery action from
  the recovery surface instead of using document-wide button queries.
- Starts with an empty stored workspace profile state so any recovered workspace
  rows must appear because the live retry path completed successfully.

## Expected result

```text
Pass: the recovery action ("Sync issue" ticket variant or live "Retry" label)
re-requests the blocked startup artifact, clears the failed startup surface,
restores the interactive shell, and the workspace switcher shows saved
workspace rows plus the footer controls.
```

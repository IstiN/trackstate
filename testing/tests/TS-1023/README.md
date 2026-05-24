# TS-1023

Verifies that the live hosted retry recovery path restores the workspace
switcher footer and re-enables `Save and switch` after the user selects a
different recovered workspace row.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1023/test_ts_1023.py
```

## Required environment and config

- Python 3
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Optional:
  - `TRACKSTATE_LIVE_APP_URL`
  - `TRACKSTATE_LIVE_SETUP_REPOSITORY`
  - `TRACKSTATE_LIVE_SETUP_REF`

## Expected result

```text
Pass: after Retry recovers from the visible hosted Sync issue state, the live
workspace switcher shows both Add workspace and Save and switch in the footer.
Save and switch is initially disabled, then becomes enabled after a different
saved workspace row is selected.
```

# TS-683 test automation

Verifies the deployed TrackState app handles malformed preloaded browser state
during startup by repairing the data, logging the inconsistency, and keeping the
interactive shell visible.

The automation:
1. injects malformed raw values into the Flutter web saved-workspace and hosted
   token browser preference keys
2. launches the deployed app in Chromium
3. verifies startup rewrites the malformed values into Flutter web's encoded
   SharedPreferences format
4. monitors browser console/page diagnostics for a descriptive guard log
5. verifies the visible shell still shows the main navigation and dashboard
   content instead of failing startup

## Install dependencies

```bash
python3 -m pip install --user playwright
python3 -m playwright install chromium
```

## Run this test

```bash
PYTHONPATH=. python3 testing/tests/TS-683/test_ts_683.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`
- Optional overrides:
  - `TRACKSTATE_LIVE_APP_URL`
  - `TRACKSTATE_LIVE_SETUP_REPOSITORY`
  - `TRACKSTATE_LIVE_SETUP_REF`

## Expected result

```text
Pass: startup repairs the malformed preloaded browser values, emits a
descriptive diagnostic log about the inconsistency, and still reaches the
interactive TrackState shell.

Fail: startup does not repair the malformed preload, does not emit a descriptive
diagnostic log, or does not keep the interactive shell visible.
```

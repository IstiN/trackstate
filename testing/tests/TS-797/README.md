# TS-797 test automation

Verifies that the live TrackState workspace switcher stays open and keeps its
current state while the viewport changes from desktop to compact/mobile and back
again, morphing from an anchored panel to a bottom sheet and back to an
anchored panel.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
PYTHONPATH=. python3 testing/tests/TS-797/test_ts_797.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the live workspace switcher opens as an anchored desktop panel, remains
open while the viewport shrinks to compact/mobile, transitions into a mobile
bottom sheet without losing its visible state, and then returns to an anchored
desktop panel when the viewport expands again.

Fail: the switcher closes, loses its current state, opens the wrong container
type during either resize, or otherwise stops matching the live user-visible
behavior in the ticket.
```

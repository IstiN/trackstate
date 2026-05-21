# TS-838 test automation

Verifies that the live desktop TrackState workspace switcher trigger opens the
workspace switcher surface on mouse click and that the opened surface exposes
parsed visible saved-workspace rows for the preloaded hosted workspaces.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-838/test_ts_838.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: on desktop, clicking the visible workspace switcher trigger opens the
workspace switcher surface and exposes the preloaded saved workspace rows with
their active/open actions.

Fail: the click does not open the surface, or the surface opens without parsed
visible saved workspace rows for the preloaded hosted workspaces.
```

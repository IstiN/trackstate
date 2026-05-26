# TS-819 test automation

Verifies that the live desktop TrackState workspace switcher dismisses when the
user presses the `Escape` key and that focus returns to the workspace switcher
trigger afterward.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-819/test_ts_819.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: on desktop, opening the workspace switcher and then pressing Escape
closes the panel immediately and returns keyboard focus to the workspace
switcher trigger.

Fail: the panel stays open, the main shell is not restored, or focus does not
return to the workspace switcher trigger after Escape.
```

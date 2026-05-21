# TS-820 test automation

Verifies that the live desktop TrackState workspace switcher behaves like a
toggle: clicking the same trigger a second time dismisses the already-open
panel.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-820/test_ts_820.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: on desktop, opening the workspace switcher and clicking the same trigger
again closes the panel immediately.

Fail: the panel stays open, reopens, or otherwise fails to dismiss after the
second trigger click.
```

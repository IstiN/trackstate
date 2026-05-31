# TS-806 test automation

Verifies that the live desktop TrackState workspace switcher dismisses when the
user clicks a neutral area of the main application content outside the header
and outside the switcher panel.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
PYTHONPATH=. python3 testing/tests/TS-806/test_ts_806.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: on desktop, opening the workspace switcher and then clicking a neutral
area of the main content outside the panel closes the switcher immediately.

Fail: the panel stays open, reopens, or otherwise fails to dismiss after the
outside click.
```

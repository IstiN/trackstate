# TS-830

Verifies the deployed desktop TrackState top-bar keyboard order includes the
workspace switcher trigger and that the focused trigger shows a visible focus
indicator.

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-830/test_ts_830.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: keyboard Tab navigation reaches the workspace switcher trigger in logical
desktop order after Settings and immediately before the Search control, and the focused trigger
shows a visible focus indicator.
```

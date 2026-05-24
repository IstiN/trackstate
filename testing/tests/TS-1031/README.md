# TS-1031

Live Playwright regression for the startup authentication probe that must begin
promptly during app bootstrap and remain pending long enough to observe before
the shell becomes interactive.

## Run

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
mkdir -p outputs
PYTHONPATH=. python3 testing/tests/TS-1031/test_ts_1031.py
```

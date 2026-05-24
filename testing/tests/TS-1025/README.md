# TS-1025

Live Playwright regression for startup diagnostics around the delayed GitHub `/user`
auth probe fallback, using the hosted startup path and same-run browser-console
evidence from the deployed app.

## Run

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
mkdir -p outputs
PYTHONPATH=. python3 testing/tests/TS-1025/test_ts_1025.py
```

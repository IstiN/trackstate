# TS-1035

Live Playwright regression for success-path startup diagnostics around the GitHub
`/user` auth probe timing delta.

## Run

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
mkdir -p outputs
PYTHONPATH=. python3 testing/tests/TS-1035/test_ts_1035.py
```

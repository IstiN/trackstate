# TS-1033

Live Playwright regression for startup with a cached hosted session. It proves
the deployed app still dispatches the GitHub `/user` authentication probe during
bootstrap instead of bypassing that network verification because local session
state is already cached in browser storage.

The automation:
1. seeds an active hosted workspace plus stored GitHub token into browser
   storage before launch
2. delays the live GitHub `/user` probe by 5 seconds so the startup request is
   easy to observe
3. verifies the delayed `/user` request begins during bootstrap before visible
   shell markers can take over the screen
4. confirms the user-visible shell still becomes interactive after the pending
   probe is released

Linked startup fix reviewed for timing behavior: TS-1029.

## Run

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
mkdir -p outputs
PYTHONPATH=. python3 testing/tests/TS-1033/test_ts_1033.py
```

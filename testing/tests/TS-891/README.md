# TS-891

Validates that startup keeps the saved local workspace out of the
**Local Unavailable** state while GitHub auth verification is slow, then
transitions the row to **Local Git** after the delayed auth-ready signal.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored GitHub token
   and a preloaded active local workspace profile
2. delays the GitHub `/user` auth verification request to simulate 8 seconds of
   startup authentication latency
3. opens **Workspace switcher** before the delayed auth probe is released and
   verifies the saved local workspace row is visible and not marked
   `Local Unavailable`
4. waits for the delayed auth probe to finish and then waits for the visible UI
   to restore the saved workspace to the active `Local Git` state
5. reopens **Workspace switcher** and verifies the active local row is selected,
   shows `Local Git`, and keeps **Connect GitHub** hidden

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-891/test_ts_891.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: while auth verification is still delayed, the saved local workspace row is
visible and not marked Local Unavailable; after the delayed ready signal, the
workspace is restored as the selected Local Git row and does not show Connect
GitHub.

Fail: the pending-phase row is marked Local Unavailable, the app never restores
the saved workspace to Local Git after auth becomes ready, or the final row
still shows Connect GitHub.
```

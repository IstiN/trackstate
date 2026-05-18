# TS-817

Validates that startup restores a saved active local workspace as **Local Git**
instead of falling back to the hosted setup workspace.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored signed-in
   GitHub session and a preloaded active local workspace profile
2. prepares the matching local git folder on disk before startup
3. waits after startup for the workspace switcher trigger to reflect the saved
   active local workspace instead of asserting immediately
4. opens **Workspace switcher** and verifies the selected active row is the local
   workspace in the `Local Git` state
5. records the visible trigger, row state, and screenshot if startup still lands
   on the hosted fallback or marks the local row `Local Unavailable`

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-817/test_ts_817.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: after startup finishes, the prepared active local workspace is restored as
the selected active row in the Local Git state, and the app does not fall back
to Hosted setup workspace or show the local row as Local Unavailable.

Fail: startup keeps Hosted setup workspace active, leaves the local row
Unavailable, or otherwise does not restore the saved active local workspace in
the Local Git state.
```

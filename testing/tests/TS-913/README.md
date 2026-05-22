# TS-913

Validates the workspace state machine guard keeps a local workspace in
**Local Unavailable** after startup even when the folder becomes accessible again
outside the app, until the user performs a manual recovery action.

The automation:
1. preloads the saved local workspace as already unavailable while the hosted
   workspace remains active
2. opens the deployed TrackState app in Chromium and verifies the saved local
   workspace is shown as `Local Unavailable`
3. recreates the same local repository on disk without interacting with the app
4. refreshes the application and waits beyond the startup revalidation window
   again before asserting
5. opens **Workspace switcher** and verifies the local workspace still shows
   `Local Unavailable` instead of automatically recovering to `Local Git`
6. runs the browser session at the ticket-aligned desktop viewport of `1440x900`

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-913/test_ts_913.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Desktop viewport: `1440x900`
- Preloaded state: hosted workspace active, saved local workspace marked
  unavailable
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: after the local workspace is already unavailable, restoring the folder on
disk and refreshing the app does not auto-promote the workspace back to Local
Git. Workspace switcher continues to show the saved local workspace as Local
Unavailable until a manual recovery gesture occurs.

Fail: refreshing the app after the folder is restored changes the workspace to
Local Git, makes the header trigger show the local workspace as recovered, or
otherwise removes the Local Unavailable state without a manual action.
```

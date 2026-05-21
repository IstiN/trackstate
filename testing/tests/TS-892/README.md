# TS-892

Validates that startup treats a permanent local file-system failure as
**Local Unavailable** without incorrectly promoting the hosted workspace to the
active selection while the saved local configuration still exists.

The automation:
1. prepares a local git repository and deletes it before startup to reproduce a
   permanent access failure through a real missing-directory condition
2. preloads the deleted local workspace as the active saved workspace plus one
   hosted fallback workspace
3. opens the deployed TrackState app in Chromium and waits beyond the startup
   local-workspace revalidation window before asserting
4. opens **Workspace switcher** and verifies the deleted local workspace row is
   still shown as `Local Unavailable`
5. verifies the app does **not** keep `Hosted setup workspace` selected as the
   active workspace while the unavailable local configuration is still present

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-892/test_ts_892.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: after startup retry handling is exhausted, the deleted local workspace row
remains visible as Local Unavailable, and the app does not switch the active
selection to Hosted setup workspace simply because the local workspace could not
be reopened.

Fail: startup keeps Hosted setup workspace selected, restores the deleted local
workspace to Local Git, hides the unavailable local row, or otherwise does not
match the expected user-facing permanent-error state.
```

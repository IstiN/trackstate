# TS-987

Validates that the Workspace switcher recovery guard prioritizes the live sync
error state over a persisted active local-workspace selection after startup
directory mismatch.

The automation:
1. preloads a broken saved local workspace as the active startup target plus one
   hosted fallback workspace into browser storage, without pre-marking the local
   workspace unavailable
2. opens the deployed TrackState app in Chromium at `1440x900`
3. waits for startup to settle into the interactive shell and for the header sync
   status to expose the recovery-prioritized sync error label
4. opens **Workspace switcher** and verifies the seeded broken local workspace
   row is shown as `Unavailable` with a recovery action instead of `Active`

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-987/test_ts_987.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: startup reaches the interactive TrackState shell, the header sync status
reports the sync error recovery state, and Workspace switcher renders the broken
saved local workspace as Unavailable with Retry or Re-authenticate instead of
preserving the persisted Active state.

Fail: startup stalls before the shell renders, the header never exposes the sync
error state, Workspace switcher cannot be opened, or the broken local workspace
row remains Active/Local Git instead of showing the Unavailable recovery state.
```

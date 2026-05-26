# TS-964

Validates that startup uses the fail-soft pattern and still renders the
interactive shell when the saved active local workspace cannot be restored.

The automation:
1. preloads the broken saved local workspace as the active startup target plus
   one hosted fallback workspace into browser storage, without pre-marking the
   local workspace unavailable
2. opens the deployed TrackState app in Chromium at `1440x900`
3. waits for startup to settle and verifies the app does not remain on the
   terminal `Sync issue` surface
4. checks that the header workspace switcher trigger is visible and interactive
5. opens **Workspace switcher** and verifies the seeded broken local workspace
   is still visible there in the `Unavailable` state with a recovery action

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-964/test_ts_964.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: startup reaches the interactive TrackState shell instead of remaining on a
terminal Sync issue screen, the header workspace switcher trigger is visible,
and Workspace switcher opens with the configured broken local workspace still
available for manual recovery.

Fail: startup hard-stops on Sync issue, never renders the shell/header, never
exposes the workspace switcher trigger, or the opened switcher does not show the
seeded broken local workspace.
```

# TS-986

Validates that startup hydration does not keep a mismatched saved local
workspace in the persisted `Active` / `Local Git` state. Instead, the
workspace must transition to the explicit `Unavailable` recovery state after
startup finishes and the Workspace switcher is opened.

The automation:
1. preloads a broken saved local workspace as the active startup target plus
   one hosted fallback workspace into browser storage
2. opens the deployed TrackState app in Chromium at `1440x900`
3. waits for startup hydration to settle into the interactive shell
4. opens **Workspace switcher**
5. verifies the broken local workspace row is rendered as `Unavailable`, does
   not remain selected as `Active`, and exposes a recovery action such as
   `Retry`

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-986/test_ts_986.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: startup reaches the interactive shell, Workspace switcher opens, and the
broken saved local workspace row is shown as Unavailable instead of falling
back to the persisted Active / Local Git state.

Fail: startup never reaches the shell, Workspace switcher cannot be opened, or
the mismatched local workspace still renders as Active / Local Git rather than
Unavailable.
```

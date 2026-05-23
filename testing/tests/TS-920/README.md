# TS-920

Validates that canceling the browser directory picker during manual restoration
does not crash the deployed app and does not incorrectly change the saved local
workspace away from `Unavailable`.

The automation:
1. preloads one hosted workspace as active plus one saved local workspace in the
   `Unavailable` state
2. recreates the local repository on disk so the saved workspace would be
   restorable if the picker were accepted
3. opens the Workspace switcher and clicks the exact visible action exposed for
   the unavailable saved workspace row
4. simulates the browser-native cancel path by forcing
   `showDirectoryPicker(...)` to reject with `AbortError` and
   `requestPermission(...)` to resolve to `denied`
5. verifies the live app stays interactive, the hosted workspace stays active,
   and the saved local workspace remains `Unavailable`

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-920/test_ts_920.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the saved unavailable local workspace triggers the browser-access
callback, the simulated Cancel leaves the hosted workspace active, the saved
local workspace stays `Unavailable`, and no `Unsupported operation:
Process.run` or runtime page error appears.

Fail: the deployed app never reaches the workspace switcher, the manual restore
action never triggers browser access, the cancel path crashes or surfaces a
runtime exception, or the workspace state changes away from the expected
`Unavailable` + hosted-active result.
```

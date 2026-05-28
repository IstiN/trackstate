# TS-912

Validates that an unavailable saved local workspace can be restored only through
the user-visible manual action exposed from the Workspace switcher and that the
flow reaches a real browser directory-access callback before the workspace
returns to `Local Git`.

The automation:
1. preloads one hosted workspace as active plus one saved local workspace in the
   `Unavailable` state
2. recreates the local repository on disk so the saved workspace becomes
   restorable
3. opens the Workspace switcher and clicks the exact visible action exposed for
   the unavailable saved workspace row
4. records whether the deployed app invokes `showDirectoryPicker(...)` or
   `FileSystemHandle.requestPermission(...)`, but it never substitutes the
   browser picker result with a test-authored handle
5. verifies the restored workspace becomes active as `Local Git`, the shell
   stays interactive, and browser storage updates to the local workspace

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-912/test_ts_912.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the saved unavailable local workspace exposes a working manual restore
action, the deployed app triggers a real browser directory-access callback, and
the workspace becomes the active `Local Git` workspace.

Fail: the saved workspace action never triggers a directory-access callback, the
deployed app reports an access/open error instead of a re-authentication flow,
or the app reaches Chromium's native browser prompt boundary, which this
Playwright flow can record but cannot complete without substituting the picker
result.
```

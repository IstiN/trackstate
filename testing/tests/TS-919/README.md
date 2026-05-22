# TS-919

Validates that the visible primary action for a saved local workspace in the
**Local Unavailable** state is labeled `Re-authenticate` or `Retry`, and never
the stale `Open` label reported by TS-915.

The automation:
1. preloads one hosted workspace as active plus one saved local workspace whose
   directory is missing on disk
2. opens the deployed TrackState app in Chromium and waits for the interactive
   shell
3. opens **Workspace switcher** and locates the unavailable saved local
   workspace row
4. inspects the visible action button labels for that row and asserts the
   primary action is `Re-authenticate` or `Retry`

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-919/test_ts_919.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the saved unavailable local workspace row is visible in Workspace
switcher and its primary action label is `Re-authenticate` or `Retry`, not
`Open`.

Fail: the unavailable row is missing, is not shown as unavailable, or its
visible action label is `Open` or any other unexpected value.
```

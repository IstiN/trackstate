# TS-682 test automation

Verifies the deployed Saved workspaces UI stays usable when one preloaded
workspace entry contains corrupted row metadata.

The automation:
1. opens the live TrackState app in Chromium with a stored GitHub token and a
   preloaded saved-workspace state containing one valid Hosted row, one valid
   Local row, and one malformed entry whose `id` is corrupted and whose
   `targetType` is missing
2. navigates to **Project Settings**
3. verifies the **Saved workspaces** section remains visible and the valid
   Hosted and Local rows still render
4. checks the malformed entry is either skipped or shown as a safe fallback row
   without breaking the UI
5. records the repaired Flutter web storage as diagnostic evidence without
   requiring one exact normalized payload shape

## Install dependencies

```bash
python3 -m pip install --user playwright
python3 -m playwright install chromium
```

## Run this test

```bash
PYTHONPATH=. python3 testing/tests/TS-682/test_ts_682.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`
- Optional overrides:
  - `TRACKSTATE_LIVE_APP_URL`
  - `TRACKSTATE_LIVE_SETUP_REPOSITORY`
  - `TRACKSTATE_LIVE_SETUP_REF`

## Expected result

```text
Pass: the application remains stable, the valid Hosted and Local rows stay
visible, and the malformed entry is either skipped or rendered via a safe
fallback without crashing the Saved workspaces UI.

Fail: startup no longer reaches the interactive shell, the Saved workspaces
section disappears, the valid rows are missing, or the malformed entry still
surfaces clearly unsafe user-facing or persisted values.
```

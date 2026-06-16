# TS-1288

Validates that the deployed TrackState app hides the normal Create issue form
controls while the read-only recovery gate is active in a hosted session.

The automation:
1. opens the deployed hosted app in Chromium with a GitHub-backed read-only
   session patch applied
2. opens the top-bar **Create issue** entry point and waits for the live create
   surface to render in the read-only state
3. verifies the guided recovery explanation and visible **Open settings** CTA
   stay present in that create surface
4. asserts the create surface does not expose Summary, Description, Save, or
   Create controls while the recovery gate is active

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1288/test_ts_1288.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Network access to `https://istin.github.io/trackstate-setup/` and GitHub API
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the read-only Create issue dialog shows only the guided recovery gate and
Open settings CTA, with Summary/Description fields removed and save_button_count=0
plus create_button_count=0 inside the active create surface.

Fail: the read-only Create issue flow still exposes editable form controls, the
recovery gate does not render in the create surface, or Save/Create actions are
still visible while the gate is active.
```

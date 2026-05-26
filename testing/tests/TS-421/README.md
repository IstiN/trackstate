# TS-421 test automation

Verifies the hosted issue detail keeps secondary collaboration data deferred
until the user explicitly opens each tab.

The automation:
1. opens the live `DEMO-2` issue detail view in the hosted TrackState app
2. confirms the visible **Comments** and **History** tabs are present before
   activation
3. verifies no tracked comment or history requests fire during the quiet window
   after the issue opens
4. opens **Comments** and verifies requests for the seeded `comments/*.md`
   files start only then, with the seeded comment text visible in the active
   panel
5. opens **History** and verifies the deferred history request starts only
   after that tab is activated, with the expected history entry visible

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-421/test_ts_421.py
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
  - `TS421_RESULT_PATH`

## Expected result

```text
Pass: the hosted issue detail keeps Comments and History hydration deferred
until the user opens each tab, then loads the seeded collaboration data in the
active panel.

Fail: comment or history hydration starts before tab activation, the deferred
requests do not fire after activation, or the seeded collaboration content does
not appear in the visible panel.
```

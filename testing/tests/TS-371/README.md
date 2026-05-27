# TS-371 test automation

Verifies that the deployed hosted **Create issue** flow shows a guided recovery
gate when the authenticated session lacks repository write access.

The automation:
1. opens the live hosted TrackState app against the deployed setup repository
2. connects a hosted GitHub session whose repository permission response is
   patched to read-only in-browser
3. clicks the visible top-bar **Create issue** trigger and verifies the create
   surface renders the read-only gate callout instead of silently doing nothing
4. checks that the gate includes a contextual blocked-creation explanation and
   a visible **Open settings** CTA
5. performs a user-style check that clicking the CTA routes to **Project
   Settings** / **Repository access**

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-371/test_ts_371.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: clicking Create issue in a connected read-only hosted session opens the
Create issue surface, shows a guided blocked-creation explanation with an Open
settings CTA, and routes the user to Project Settings.

Fail: the Create issue trigger stays silently inert, the create surface opens
without the guidance gate, the contextual explanation or recovery CTA is
missing, or the CTA does not take the user to the settings/authentication
surface.
```

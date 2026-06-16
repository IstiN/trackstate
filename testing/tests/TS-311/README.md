# TS-311 test automation

Verifies that the hosted issue-detail route keeps collaboration content behind
dedicated **Comments**, **Attachments**, and **History** tabs, and that the
hosted **Attachments** tab stays download-only for the seeded Git LFS-backed
attachment.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-311/test_ts_311.py
```

## Required environment

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`
- Optional overrides:
  - `TRACKSTATE_LIVE_APP_URL`
  - `TRACKSTATE_LIVE_SETUP_REPOSITORY`
  - `TRACKSTATE_LIVE_SETUP_REF`

## Expected result

```text
Pass: The seeded issue opens on the Detail tab, the seeded comment and
attachment stay hidden until their respective tabs are opened, the Comments /
Attachments / History tabs are all reachable, and the hosted Attachments tab
shows the explicit download-only guidance while keeping a visible download
action for the LFS-backed attachment.

Fail: Any collaboration tab is missing, collaboration content leaks onto the
default detail surface, the hosted Attachments tab lacks the download-only
message, a hosted upload path remains usable, or the download action is missing
or disabled.
```

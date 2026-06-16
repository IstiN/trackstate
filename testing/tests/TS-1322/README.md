# TS-1322 test automation

Verifies that replacing a hosted attachment in the live TrackState setup
persists the new file bytes and updates the visible attachment row instead of
showing stale cached content.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
python3 testing/tests/TS-1322/test_ts_1322.py
```

## Required environment / config

- `GH_TOKEN` or `GITHUB_TOKEN` with write access to `IstiN/trackstate-setup`
- Network access to the hosted TrackState demo and the GitHub API
- Optional: `TRACKSTATE_LIVE_APP_URL` to override the hosted app URL

## Expected passing output

```text
TS-1322 passed: the hosted attachment was replaced, the visible row updated,
and the downloaded bytes matched the new file content.
```

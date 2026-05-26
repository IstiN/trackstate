# TS-455

Validates the hosted issue-detail **Comments** failure flow for a single deferred
artifact, including the visible tab warning state, inline **Retry** action,
continued **Detail** usability, and the AC4 requirement that retry refetches
only the failed comment artifact.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-455/test_ts_455.py
```

## Required environment and config

- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to `https://istin.github.io/trackstate-setup/` and the GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: a synthetic failure for only DEMO-2/comments/0001.md shows the Comments
error UI and warning indicator, Detail remains usable, and Retry refetches only
that failed comment artifact before clearing the error.

Fail: the outage affects more than the targeted comment artifact, Detail is
blocked, Retry does not clear the error, or Retry refetches any comment artifact
other than the originally failed one.
```

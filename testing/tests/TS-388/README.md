# TS-388

Validates the deployed issue-detail collaboration ordering for the live
`DEMO-2` issue.

The automation:
1. opens the hosted tracker with a stored GitHub token
2. navigates to the live `DEMO-2` issue detail
3. verifies visible **Comments** rows stay oldest-to-newest
4. verifies visible **Attachments** rows stay newest-to-oldest, or records the
   exact user-visible error if the attachment list cannot render

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-388/test_ts_388.py
```

## Required environment and config

- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to `https://istin.github.io/trackstate-setup/` and the GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the live Comments tab shows the oldest comment at the top and the newest
comment at the bottom, and the live Attachments tab shows the newest attachment
at the top and the oldest at the bottom.

Fail: either tab does not render a stable list, the visible order is wrong, or
the Attachments tab surfaces a user-visible load error instead of a sortable
attachment list.
```

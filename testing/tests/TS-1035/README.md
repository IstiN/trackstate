# TS-1035

Live Playwright regression for success-path startup diagnostics around the GitHub
`/user` auth probe timing delta.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Environment

- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Optional: `TRACKSTATE_LIVE_APP_URL` (defaults to `https://istin.github.io/trackstate-setup/`)
- Optional: `TRACKSTATE_LIVE_SETUP_REPOSITORY` (defaults to `IstiN/trackstate-setup`)
- Optional: `TRACKSTATE_LIVE_SETUP_REF` (defaults to `main`)

## Run

```bash
mkdir -p outputs
PYTHONPATH=. python3 testing/tests/TS-1035/test_ts_1035.py
```

## Expected pass output

- Console output ends with `TS-1035 passed`
- `outputs/test_automation_result.json` contains `"status": "passed"`
- `outputs/jira_comment.md`, `outputs/pr_body.md`, and `outputs/response.md` are refreshed for the latest live run

# TS-409 test automation

Verifies that the hosted **Project Settings** flow writes the edited status and
workflow changes in one Git commit and that the hosted `trackstate session`
response exposes the updated `projectConfig` immediately afterward.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-409/test_ts_409.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- `TRACKSTATE_LIVE_APP_URL` pointing at the deployed hosted TrackState app
- Defaults come from `testing/core/config/live_setup_test_config.py`
- The hosted CLI parity step requires the installed `trackstate` executable on
  `PATH`; it does not fall back to `dart run trackstate`

## Scenario notes

- The test drives the live hosted Settings UI, adds a unique status, updates the
  Delivery Workflow transition label, and saves the configuration.
- The scenario uses a desktop viewport of `1440x900` for consistent live UI
  verification.
- The repository head check uses elapsed-time polling so a Step 4 failure means
  the hosted save did not publish a new commit within the configured window.
- Even when the Git persistence step fails, the test still runs the hosted
  `trackstate session` CLI so the output captures whether `projectConfig`
  reflects the attempted change.
- The test restores the original hosted repository configuration during cleanup
  when the mutation succeeds.

## Expected passing output

- `outputs/test_automation_result.json` contains `{ "status": "passed", ... }`
- `outputs/jira_comment.md`, `outputs/pr_body.md`, and `outputs/response.md`
  describe the successful hosted save, Git commit verification, and CLI parity check

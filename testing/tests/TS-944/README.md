# TS-944

## Objective

Verify that the hosted accessibility workflow still logs the early Flutter engine
startup milestones when the Flutter web engine crashes before the accessibility
runtime reaches the `surface ready` state.

## Automation approach

1. Create a disposable pull request against `main`.
2. Change only `testing/accessibility/` files so the live accessibility gate
   simulates an early Flutter web engine crash.
3. Wait for the real `Flutter Required Checks` workflow and inspect the hosted
   `Accessibility checks` log.
4. Confirm the log still shows the initial `Flutter engine initialization`
   entries and does not reach `Accessibility runtime surface ready`.

## Install dependencies

```bash
python3 --version
gh auth status
```

The test uses the existing repository Python modules plus an authenticated
GitHub CLI session with permission to create disposable pull requests and read
GitHub Actions logs.

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-944/test_ts_944.py
```

## Required environment

- `gh` authenticated with push access to `IstiN/trackstate`
- Network access to GitHub pull requests, checks, and Actions logs
- Runtime settings from `testing/tests/TS-944/config.yaml`

## Expected passing output

- `outputs/test_automation_result.json` contains `"status": "passed"`
- `outputs/jira_comment.md`, `outputs/pr_body.md`, and `outputs/response.md`
  describe the live run, the visible startup tokens, and the human-style
  verification of the GitHub Actions log

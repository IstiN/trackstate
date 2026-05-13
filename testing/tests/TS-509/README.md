# TS-509 test automation

Validates that the hosted **Attachments** tab bypasses the local Git / Git LFS
warning path for browser uploads when the project is configured for
`github-releases` attachment storage and release-backed writes are available.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-509/test_ts_509.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Scenario notes

- The test opens the live hosted `DEMO-2` issue in the deployed app.
- It temporarily switches `DEMO/project.json` to
  `attachmentStorage.mode = github-releases` with a ticket-specific release tag
  prefix.
- It selects a file that matches a real Git LFS-tracked extension from the live
  repository `.gitattributes`, uploads it through the browser UI, and verifies
  the attachment manifest plus GitHub Release asset state.
- It waits for the live Attachments panel to finish hydrating after the project
  config change before interacting with the upload controls, and it captures the
  visible panel state on failure.
- A passing result means the user never sees the hosted local-Git/LFS warning,
  the upload controls stay enabled, and the upload lands in the release-backed
  attachment flow.

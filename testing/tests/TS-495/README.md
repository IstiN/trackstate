# TS-495 test automation

Validates that hosted **Repository access** shows the GitHub Releases success
state when the project uses `github-releases` attachment storage and the
connected provider session supports release-backed browser uploads.

## Install dependencies

```bash
python -m pip install playwright pillow
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-495/test_ts_495.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository with write access
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Scenario notes

- The test temporarily updates `DEMO/project.json` so attachment storage uses
  `github-releases` with a ticket-specific release tag prefix.
- It opens the deployed hosted TrackState app with a stored token session and
  navigates to `Project Settings`.
- A passing result means the top Repository access band stays connected, the
  secondary `GitHub Releases attachment storage` callout uses success styling,
  its copy explicitly states that release-backed browser uploads are supported,
  and the blanket `Some attachment uploads still require local Git` warning is
  not shown.

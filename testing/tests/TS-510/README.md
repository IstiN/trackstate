# TS-510 test automation

Validates that replacing a legacy repository-path attachment with a
release-backed upload keeps only the new active entry visible in the hosted
**Attachments** tab.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-510/test_ts_510.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Scenario notes

- The test seeds the existing hosted `DEMO-2` issue with a legacy
  `manual.pdf` repository-path attachment manifest entry, then switches
  `DEMO/project.json` to `attachmentStorage.mode = github-releases`.
- A passing result means the deployed UI lets the user replace `manual.pdf`,
  the refreshed Attachments tab shows exactly one visible `manual.pdf` entry,
  and `attachments.json` contains a single `manual.pdf` entry with
  `storageBackend = github-releases`.
- A failing result is still valid evidence when the hosted product leaves
  duplicate rows, does not update the manifest, or blocks the live replacement
  flow.

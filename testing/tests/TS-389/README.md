# TS-389 test automation

Verifies that the hosted **Attachments** flow does not silently overwrite an
existing attachment when a newly selected file resolves to the same sanitized
storage name.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-389/test_ts_389.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- `TRACKSTATE_LIVE_APP_URL` pointing at the deployed hosted TrackState app
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Scenario notes

- The test seeds `design_doc.pdf` into the demo repository when that attachment
  is missing, then restores the original repository state during cleanup.
- A passing result means the live UI exposes the upload controls, shows the
  explicit replacement confirmation copy, keeps the repository unchanged before
  confirmation, and only updates the attachment after the user confirms.
- A failing result is still valid evidence when the hosted product does not
  expose the required upload or replacement-confirmation path; in that case the
  test writes bug output instead of masking the product gap.

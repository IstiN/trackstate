# TS-887

Automates the hosted **Edit issue** Summary-validation accessibility scenario
for `DEMO-2` from the user's perspective.

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Required environment

- `GH_TOKEN` or `GITHUB_TOKEN`: fine-grained GitHub token that can connect the
  hosted `IstiN/trackstate-setup` workspace and edit issues
- Optional:
  - `TRACKSTATE_LIVE_APP_URL` (defaults to `https://istin.github.io/trackstate-setup/`)
  - `TRACKSTATE_LIVE_SETUP_REPOSITORY` (defaults to `IstiN/trackstate-setup`)
  - `TRACKSTATE_LIVE_SETUP_REF` (defaults to `main`)

## Run this test

```bash
mkdir -p outputs
PYTHONPATH=. python3 testing/tests/TS-887/test_ts_887.py
```

## Expected output

```text
PASS: the Summary field is editable, Save keeps the Edit dialog open, the UI
shows Summary-required validation feedback, the visible message meets WCAG AA
contrast, and the error text is reachable to assistive technology.

FAIL: the hosted Edit issue flow does not expose that user-visible validation
state (for example, the field cannot be cleared, Save closes the dialog, the
message is missing, contrast is too low, or the error is not announced).
```

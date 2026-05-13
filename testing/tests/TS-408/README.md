# TS-408 test automation

Validates the hosted **Settings > Fields** workflow against
`https://istin.github.io/trackstate-setup/`, covering both reserved-field
protection and custom-field creation.

The automation:
1. opens the live **Fields** administration screen
2. verifies the reserved **Summary** row stays protected from delete and keeps
   its immutable metadata
3. creates an **Environment** custom field as a select/option field with three
   option values
4. saves the hosted field catalog and re-opens the saved field editor
5. verifies the saved **Environment** field applies only to **Bug**

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-408/test_ts_408.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`
- Optional overrides:
  - `TRACKSTATE_LIVE_APP_URL`
  - `TRACKSTATE_LIVE_SETUP_REPOSITORY`
  - `TRACKSTATE_LIVE_SETUP_REF`
  - `TS408_RESULT_PATH`

## Expected result

```text
Pass: the hosted Settings > Fields screen keeps the reserved Summary field
immutable, creates the Environment select field with three options, and saves it
with Bug-only applicability.

Fail: the hosted UI exposes mutable Summary metadata, cannot create/save the
Environment field, or loses the saved field metadata/applicability after save.
```

# TS-466

Validates the live hosted **Settings > Locales** workflow for multi-catalog
translation editing and fallback indicators.

The automation:
1. opens the deployed tracker settings UI
2. ensures a second locale exists for the live repository
3. verifies the Locales tab exposes all seven required metadata catalogs
4. enters a translation for a real priority ID
5. leaves a real status translation empty and verifies the inline fallback warning
6. saves the live settings and confirms the persisted result
7. restores the repository state after verification

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-466/test_ts_466.py
```

## Required environment and config

- `GH_TOKEN` or `GITHUB_TOKEN` that can authenticate against
  `IstiN/trackstate-setup`
- network access to the hosted app and the GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: Settings > Locales exposes statuses, issue types, fields, priorities,
components, versions, and resolutions; a priority translation can be edited; an
empty status translation shows the inline fallback warning with the English
label; and the save path persists the visible result.

Fail: the live app does not expose the Locales editing workflow, any mandatory
catalog is missing, the inline fallback warning is absent or wrong, or the save
path does not persist the user-visible translation state.
```

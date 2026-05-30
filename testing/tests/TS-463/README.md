# TS-463

Validates the live hosted **Settings** catalog-management workflow for
**Priorities**, **Components**, and **Versions** against
`https://istin.github.io/trackstate-setup/`.

The automation:
1. opens the deployed tracker settings UI
2. navigates to **Settings > Priorities**
3. creates a new priority with ID `ultra` and name `Ultra High`
4. opens **Settings > Components** and attempts to rename an existing component
   while preserving its canonical ID
5. opens **Settings > Versions** and deletes a disposable unused version
6. saves the live settings and verifies the persisted repository JSON
7. restores the repository catalog files after verification

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-463/test_ts_463.py
```

## Required environment and config

- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to the hosted app and the GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: Settings > Priorities, Components, and Versions support the requested
CRUD flow; the saved repository JSON reflects the changes; and canonical IDs are
preserved where required.

Fail: the hosted app does not expose the required catalog-edit behavior, the
save path does not persist the expected repository state, or the UI does not
present the expected live catalog changes.
```

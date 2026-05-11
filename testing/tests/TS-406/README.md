# TS-406 test automation

Verifies the hosted **Project settings administration** flow can create a named
workflow and assign it to a specific issue type.

The automation:
1. opens the deployed tracker and reaches **Settings > Workflows**
2. creates **Bug Workflow** with only **To Do** and **Done** statuses plus a
   **To Do -> Done** transition when that workflow does not already exist
3. edits the **Bug** issue type so it uses **Bug Workflow**
4. saves project settings
5. verifies persistence from both the visible hosted UI and the repository-backed
   `DEMO/config/workflows.json` and `DEMO/config/issue-types.json`

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-406/test_ts_406.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with write access to `IstiN/trackstate-setup`
- network access to the hosted app and GitHub API

## Expected result

```text
Pass: Project settings can create or surface the named Bug Workflow, the Bug
issue type can be assigned to it, the visible Settings UI persists the change,
and the repository config links Bug to workflow ID bug-workflow.

Fail: The hosted settings UI does not expose the required controls, the save
path does not persist, or the repository config still keeps Bug on the default
delivery workflow.
```

# TS-524 test automation

Verifies that a hosted issue detail **Attachments** tab keeps the visible
upload controls available when the issue already contains a legacy
`repository-path` attachment and the project is configured for
`github-releases` attachment storage.

The automation:
1. seeds `DEMO-2` with a legacy `ts524-legacy-manual.pdf` attachment entry and
   switches `DEMO/project.json` to `attachmentStorage.mode = github-releases`
2. opens the deployed hosted TrackState app with a stored GitHub token
3. opens the seeded issue and switches to the **Attachments** tab
4. verifies the legacy attachment row stays visible and the tab still exposes
   one visible **Choose attachment** control plus one visible
   **Upload attachment** control
5. selects a real temporary file and verifies the user-visible selected-file
   summary appears while **Upload attachment** becomes enabled

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-524/test_ts_524.py
```

## Required environment / config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a GitHub token that can authenticate
  against the hosted setup repository
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected pass / fail behavior

- **Pass:** the hosted **Attachments** tab still shows one visible
  **Choose attachment** control and one visible **Upload attachment** control
  with the legacy attachment row present, and selecting a file enables
  **Upload attachment** while showing the selected file name and size.
- **Fail:** the legacy attachment forces the hosted tab into a read-only state,
  either upload control is missing, the choose control is disabled, or selecting
  a file does not enable **Upload attachment** and show the selected-file
  summary.

# TS-605

Verifies keyboard users can tab through the deployed hosted *Project Settings → Repository
access* controls without focus skipping the visible remember/connect actions.

The automation:
1. opens the deployed hosted TrackState app in a Chromium Playwright session using the
   configured GitHub token
2. navigates to *Project Settings → Repository access*
3. confirms the visible *Fine-grained token*, *Remember on this browser*, and
   *Connect token* controls are present in the repository-access section
4. focuses the *Fine-grained token* field and verifies successive `Tab` presses move
   to *Remember on this browser* and then *Connect token*
5. writes the required result artifacts to `outputs/`

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-605/test_ts_605.py
```

## Required environment / config

Requires `GH_TOKEN` or `GITHUB_TOKEN` for the live hosted app session. The defaults are:

- app URL: `https://istin.github.io/trackstate-setup/`
- repository: `IstiN/trackstate-setup`
- ref: `main`

## Expected passing output

```text
TS-605 passed
```

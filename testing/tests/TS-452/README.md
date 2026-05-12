# TS-452

Validates the hosted Search/Detail issue view preserves the selected issue
header and visible issue list during the initial **Detail** hydration, then
keeps only the **Comments** panel loading while the rest of the UI remains
interactive and allows switching to another issue before Comments hydration
finishes.

## Install dependencies

```bash
python -m pip install playwright
python -m playwright install chromium
```

## Run this test

```bash
python testing/tests/TS-452/test_ts_452.py
```

## Required environment and config

- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to `https://istin.github.io/trackstate-setup/` and the GitHub API
- defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: selecting DEMO-2 keeps the issue header and adjacent issue list visible
while only the Detail section shows its loading skeleton, then opening Comments
shows a Comments-only loading state and the user can switch to DEMO-3 before the
delayed DEMO-2 comment fetch completes.

Fail: opening DEMO-2 hides the selected header or list context during Detail
hydration, any non-target section shows a loading state, or switching issues
waits for the delayed Comments hydration to finish.
```

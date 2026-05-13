# TS-668 test automation

Verifies the deployed workspace management UI renders saved workspaces as
compact, accessible rows for both hosted and local targets.

The automation:
1. opens the live TrackState app in Chromium with a stored GitHub token and a
   preloaded saved-workspace state that contains one hosted row and one local row
2. navigates to **Project Settings**
3. verifies the **Saved workspaces** section renders both rows with explicit
   `Hosted` / `Local` text labels
4. checks the selected row uses the `primarySoft` background and `primary`
   outline token colors
5. checks each row exposes a non-empty semantics label plus accessible action
   labels, and that visible row text meets WCAG AA contrast expectations

## Install dependencies

```bash
python3 -m pip install --user playwright
python3 -m playwright install chromium
```

## Run this test

```bash
PYTHONPATH=. python3 testing/tests/TS-668/test_ts_668.py
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

## Expected result

```text
Pass: Project Settings shows a Saved workspaces card with one Hosted row and one
Local row, both with non-empty semantics labels, visible Hosted/Local text, and
token-compliant selected-row colors/contrast.

Fail: the Saved workspaces card is missing, one of the target rows is missing,
type labels are absent, semantics labels are empty, or the selected row does
not use the expected primary/primarySoft token colors.
```

# TS-868 test automation

Verifies that the live desktop TrackState workspace switcher supports `Home` and
`End` keyboard navigation by moving both the active selection and DOM focus to
the first and last saved workspace rows.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
   and three preloaded saved hosted workspaces
2. opens the desktop workspace switcher from Dashboard
3. confirms the first saved workspace row starts active and the second plus last
   rows are present
4. presses `ArrowDown` once to establish the ticket precondition that the second
   saved workspace row is selected and focused
5. presses `Home` and verifies the first saved workspace row becomes selected and
   focused while the switcher remains visible
6. presses `End` and verifies the last saved workspace row becomes selected and
   focused while the switcher remains visible

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-868/test_ts_868.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: with the second saved workspace row selected, pressing Home moves the
selection and focused row button to Hosted main workspace, and pressing End then
moves the selection and focused row button to Hosted end workspace while the
workspace switcher stays open.

Fail: the panel closes, fewer than three saved workspace rows are visible, the
second-row precondition cannot be established, or Home/End does not move both
selection and keyboard focus to the expected boundary row button.
```

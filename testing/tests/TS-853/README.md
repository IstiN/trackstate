# TS-853 test automation

Verifies that the live desktop TrackState workspace switcher wraps selection
from the first saved workspace row to the last when a keyboard user presses
`ArrowUp`.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
   and two preloaded saved hosted workspaces
2. opens the desktop workspace switcher from Dashboard
3. confirms the first saved workspace row is already the active/highlighted row
4. clicks the active first saved-workspace row and confirms the focused element
   is the clicked row button inside the open switcher
5. presses `ArrowUp` and waits for the active saved workspace to wrap to the
   last visible row while the panel stays open

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-853/test_ts_853.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the first saved workspace row starts active, clicking it focuses that row
inside the open workspace switcher, and ArrowUp wraps the active selection from
Hosted main workspace to Hosted alt workspace while the panel remains visible.

Fail: the first row is not active at the start, clicking the row leaves focus on
the global view or trigger, or ArrowUp does not wrap the active selection to the
last visible saved workspace row.
```

# TS-856 test automation

Verifies that the live desktop TrackState workspace switcher moves selection and
keyboard focus from the first saved workspace row to the next one when a
keyboard user presses `ArrowDown`.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
   and two preloaded saved hosted workspaces
2. opens the desktop workspace switcher from Dashboard
3. confirms the first saved workspace row is already the active/highlighted row
4. records the original keyboard focus target without clicking any saved
   workspace row
5. presses `ArrowDown` from that original state and waits for the active saved
   workspace to move to the next visible row while the panel stays open
6. asserts that the focused element after `ArrowDown` is the next row button
   itself rather than a nested control inside that row

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-856/test_ts_856.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` set to a token that can open
  `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the first saved workspace row starts active, ArrowDown is sent without any
extra row click, and the active selection moves to Hosted alt workspace while
the panel remains visible and focus lands on the Hosted alt workspace row
button itself.

Fail: the first row is not active at the start, the original switcher state
cannot be observed reliably, or ArrowDown does not move the active selection and
keyboard focus to the next visible saved workspace row button.
```

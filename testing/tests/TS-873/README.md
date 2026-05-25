# TS-873 test automation

Verifies that the live desktop TrackState workspace switcher sends selection and
keyboard focus to the correct list boundaries when desktop users press `Home`
and `End` inside the saved-workspace row list.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
   and three preloaded saved hosted workspaces
2. opens the desktop workspace switcher from Dashboard
3. explicitly focuses the active first saved-workspace row and asserts that the
   row-list keyboard precondition is established before boundary navigation is used
4. presses Arrow Down to move selection and keyboard focus to the second saved
   workspace row
5. presses `Home` and verifies selection, focus, and roving `tabindex` move to
   the first saved workspace row
6. presses `End` and verifies selection, focus, and roving `tabindex` move to
   the last saved workspace row

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-873/test_ts_873.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: pressing Home moves selection and keyboard focus to the first saved
workspace row, pressing End moves them to the last saved workspace row, and only
the selected row keeps tabindex='0' after each key press.

Fail: Home or End leaves selection on the wrong row, keyboard focus escapes the
row list, or inactive rows remain sequentially keyboard-focusable.
```

# TS-867 test automation

Verifies that the live desktop TrackState workspace switcher uses a roving
`tabindex` pattern for saved workspace rows, so only the selected row remains in
the sequential Tab order.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
   and three preloaded saved hosted workspaces
2. opens the desktop workspace switcher from Dashboard
3. explicitly focuses the active first saved-workspace row and asserts that the
   row-list keyboard precondition is established before Arrow Down is used
4. presses Arrow Down to move selection and keyboard focus to the second saved
   workspace row
5. verifies Tab leaves the row list without landing on inactive rows
6. verifies Shift+Tab returns directly to the selected second row
7. verifies another Tab still skips the inactive first and third rows

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-867/test_ts_867.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: only the selected second saved workspace row remains in the sequential Tab
order, Shift+Tab re-enters the list on that same row, and inactive rows keep
tabindex='-1'.

Fail: focus falls back to the trigger, Tab or Shift+Tab lands on an inactive
saved-workspace row, or inactive rows remain sequentially keyboard-focusable.
```

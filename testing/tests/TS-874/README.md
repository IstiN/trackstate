# TS-874

Verifies that, in the deployed desktop TrackState web app, pressing `Escape`
while the workspace switcher is open and keyboard focus is on a saved workspace
row closes the panel and restores focus to the workspace switcher trigger with a
visible focus indicator.

The automation:
1. launches the deployed TrackState app in Chromium with a stored hosted token
   and preloaded saved workspace profiles
2. opens the desktop workspace switcher and moves keyboard focus onto the
   selected saved workspace row
3. presses `Escape` from that focused row and confirms the panel dismisses
4. confirms keyboard focus is back on the workspace switcher trigger, the
   trigger shows a visible focus indicator, and `Enter` can reopen the switcher
   without any mouse interaction

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-874/test_ts_874.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: when the workspace switcher is open and a saved workspace row owns
keyboard focus, pressing Escape closes the panel immediately, restores focus to
the workspace switcher trigger, and shows a visible focus indicator on that
trigger.
```

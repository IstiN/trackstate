# TS-875

Verifies that, in the deployed desktop TrackState web app, pressing
`ArrowDown` while keyboard focus is on the internal `Save and switch` button
inside the workspace switcher advances the active saved workspace selection to
the next workspace without closing the panel.

The automation:
1. launches the deployed TrackState app in Chromium with a stored hosted token
   and two preloaded saved hosted workspaces
2. opens the desktop workspace switcher from Dashboard and confirms Hosted main
   workspace starts selected
3. moves keyboard focus onto the visible `Save and switch` button inside the
   open switcher and confirms focus remains owned by the switcher
4. presses `ArrowDown` from that focused button and verifies the active saved
   workspace advances to Hosted alt workspace while the panel remains open

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-875/test_ts_875.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: when the desktop workspace switcher is open and the visible Save and
switch button owns keyboard focus, pressing ArrowDown advances the active saved
workspace selection to the next visible saved workspace while the panel remains
open.
```

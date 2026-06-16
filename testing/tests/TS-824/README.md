# TS-824

Verifies that, on the desktop web app, the workspace switcher can be opened
from a keyboard-focused trigger, that `Tab` then moves focus into a visible
interactive element inside the open panel, and that pressing `Escape` from that
internal focused element dismisses the panel while restoring keyboard focus to
the workspace switcher trigger.

The automation:
1. launches the deployed TrackState app in Chromium with a stored hosted token
2. runs the live desktop flow at the standard `1440x900` viewport
3. tabs through the visible desktop shell until the workspace switcher trigger
   owns keyboard focus
4. opens the workspace switcher from that focused trigger and confirms the
   visible desktop panel is rendered
5. presses `Tab` once to verify focus moves from the trigger into a visible
   element inside the panel
6. presses `Escape` from that internal focused element and confirms the panel
   dismisses and the trigger is immediately keyboard-usable again

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-824/test_ts_824.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: once the workspace switcher is opened from a keyboard-focused trigger,
pressing Tab moves focus to a visible control inside the panel, pressing Escape
closes the panel immediately, and keyboard focus is restored to the workspace
switcher trigger so Enter can reopen it without any mouse interaction.
```

# TS-335

Validates on the live hosted TrackState app that the production-visible
**Create issue** form opens as a true full-screen surface on a `390x844`
mobile viewport.

The automation:
1. opens the deployed hosted app in Chromium at an exact `390x844` viewport
2. connects GitHub write access so the live Create issue action is enabled
3. opens the real Create issue surface from the running hosted shell
4. confirms the visible heading, key controls, labeled inputs, and actions a
   user relies on
5. measures the rendered dialog bounds from the live semantics tree and verifies
   it fills the viewport from origin `(0, 0)` without side or bottom insets

## Run this test

```bash
python -m pip install playwright
python -m playwright install chromium
python testing/tests/TS-335/test_ts_335.py
```

## Expected result

```text
Pass: the live hosted Create issue form opens on a 390x844 viewport as a
full-screen mobile surface at origin (0,0) with no side or bottom insets, and
the user-visible form content remains rendered in the dialog.

Fail: the hosted form does not open, loses expected visible controls, renders
inset, or leaves any side/bottom gap instead of occupying the full viewport.
```

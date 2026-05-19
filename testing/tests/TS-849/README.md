# TS-849 test automation

Verifies that the live desktop TrackState workspace switcher trigger exposes an
`aria-controls` attribute and that the attribute points to the id of the opened
workspace switcher surface.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
2. navigates to Dashboard and resizes to a desktop viewport
3. locates the visible workspace switcher trigger and inspects its ARIA-focused
   DOM attributes before opening the switcher
4. opens the workspace switcher surface from the trigger
5. compares the trigger `aria-controls` value with the visible opened surface id

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-849/test_ts_849.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: the visible desktop workspace switcher trigger exposes aria-controls
before opening the switcher, and that value matches the id of the visible
opened workspace switcher surface.

Fail: the trigger does not expose aria-controls, the referenced element does
not exist or is not visible, or the value does not match the opened surface id.
```

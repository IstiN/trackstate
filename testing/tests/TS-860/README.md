# TS-860 test automation

Verifies that the live desktop TrackState workspace switcher trigger exposes an
`aria-controls` attribute on initial page load and that the initial value
matches the id of the actual workspace switcher surface when it is opened.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
2. navigates to Dashboard and resizes to a desktop viewport
3. locates the visible workspace switcher trigger and records its initial
   `aria-controls` value before any interaction
4. opens the workspace switcher surface
5. compares the initial `aria-controls` value with the visible surface id

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-860/test_ts_860.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: the visible desktop workspace switcher trigger exposes aria-controls on
initial page load, and that initial value matches the id of the opened
workspace switcher surface.

Fail: the trigger does not expose aria-controls on initial load, the opened
workspace switcher surface does not expose an id, or the initial aria-controls
value does not match the opened surface id.
```

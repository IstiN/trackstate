# TS-860 test automation

Verifies that the live desktop TrackState workspace switcher trigger exposes an
`aria-controls` attribute on initial page load, that the initial value already
points at a DOM node before any click, and that the same value matches the id
of the actual workspace switcher surface when it is opened.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
2. navigates to Dashboard and resizes to a desktop viewport
3. locates the visible workspace switcher trigger and records its initial
   `aria-controls` value before any interaction
4. verifies before any click that the referenced DOM node already exists
5. opens the workspace switcher surface
6. compares the initial `aria-controls` value with the visible surface id

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
initial page load, that initial value already references a DOM node before any
interaction, and that same value matches the id of the opened workspace
switcher surface.

Fail: the trigger does not expose aria-controls on initial load, the opened
workspace switcher surface does not expose an id, the referenced DOM node does
not exist before interaction, or the initial aria-controls value does not match
the opened surface id.
```

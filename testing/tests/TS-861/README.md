# TS-861 test automation

Verifies that the live desktop TrackState workspace switcher keeps a persistent
`aria-controls` relationship to the same visible switcher surface across
multiple open/close toggle cycles.

The automation:
1. opens the deployed TrackState web app in Chromium with a stored hosted token
2. navigates to Dashboard and resizes to a desktop viewport
3. records the visible workspace switcher trigger `aria-controls` value before opening the switcher
4. opens the workspace switcher and confirms the visible surface `id` matches the initial trigger value
5. closes the switcher through the trigger and checks the trigger still exposes the same `aria-controls`
6. reopens the switcher and confirms the visible surface still matches the initial trigger value

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-861/test_ts_861.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: the visible desktop workspace switcher trigger keeps the same
aria-controls value before and after repeated toggle cycles, and the opened
workspace switcher surface keeps the matching id.

Fail: the trigger aria-controls value changes, disappears, or stops matching the
visible opened surface id after the panel is closed and reopened.
```

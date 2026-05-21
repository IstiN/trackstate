# TS-832

Verifies that, on the desktop web app, reverse keyboard navigation returns from
the interactive element immediately after the workspace switcher trigger back to
that trigger and restores a visible keyboard focus indicator.

The automation:
1. launches the deployed TrackState app in Chromium with a stored hosted token
2. tabs through the visible desktop shell until the workspace switcher trigger
   owns keyboard focus
3. presses `Tab` once to move focus to the next visible interactive element
4. presses `Shift+Tab` from that subsequent element
5. confirms focus returns to the workspace switcher trigger and that the trigger
   exposes a visible keyboard focus indicator again

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-832/test_ts_832.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: after keyboard focus moves forward from the workspace switcher trigger to
the next visible interactive control, pressing Shift+Tab moves focus backward to
the workspace switcher trigger and the trigger shows a visible focus indicator.
```

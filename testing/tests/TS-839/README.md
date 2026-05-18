# TS-839

Verifies that the desktop TrackState workspace switcher trigger opens the
workspace switcher surface when a keyboard user presses `Space`.

The automation:
1. launches the deployed TrackState app in Chromium with a stored hosted token
2. navigates to Dashboard and resizes to a desktop viewport
3. uses a real keyboard navigation path until the workspace switcher trigger owns
   keyboard focus
4. presses `Space` on the focused trigger
5. confirms the visible workspace switcher surface opens with the expected title

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-839/test_ts_839.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: after the workspace switcher trigger receives real keyboard focus, pressing
Space opens the visible workspace switcher surface.
```

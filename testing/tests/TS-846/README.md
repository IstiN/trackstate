# TS-846

Verifies that the condensed/mobile TrackState workspace switcher trigger opens
the visible workspace switcher surface when a keyboard user presses `Space`.

The automation:
1. launches the deployed TrackState app in Chromium with a stored hosted token
2. navigates to Dashboard and resizes the viewport to a compact mobile width
3. confirms the visible trigger is the condensed/mobile workspace switcher
4. uses a real keyboard navigation path until the trigger owns focus
5. presses `Space` on the focused trigger
6. confirms the visible workspace switcher sheet/overlay opens with its title

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-846/test_ts_846.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: after the condensed/mobile workspace switcher trigger receives real
keyboard focus, pressing Space opens the visible workspace switcher mobile
surface.
```

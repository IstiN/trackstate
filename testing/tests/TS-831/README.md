# TS-831

Verifies that, on the desktop web app, the workspace switcher trigger behaves
like a semantic button when activated with the keyboard `Space` key.

The automation:
1. launches the deployed TrackState app in Chromium with a stored hosted token
2. tabs through the visible desktop shell until the workspace switcher trigger
   owns keyboard focus
3. presses `Space` on that focused trigger and confirms the visible desktop
   workspace switcher panel opens immediately
4. continues keyboard `Tab` navigation after the Space-opened panel appears and
   confirms focus reaches a visible interactive element inside the panel

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-831/test_ts_831.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: after real keyboard Tab navigation reaches the visible workspace switcher
trigger, pressing Space opens the workspace switcher panel immediately and
subsequent keyboard Tab navigation reaches a visible control within the open
panel without any mouse interaction.
```

# TS-850

Verifies that the desktop TrackState workspace switcher trigger keeps its
`aria-expanded` state in sync with mouse-click activation.

The automation:
1. launches the deployed TrackState app in Chromium with a stored hosted token
2. locates the visible desktop workspace switcher trigger on Dashboard
3. confirms the trigger exposes `aria-expanded="false"` before opening
4. clicks the trigger to open the workspace switcher surface and confirms
   `aria-expanded="true"`
5. clicks the trigger again to dismiss the surface and confirms
   `aria-expanded="false"`

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-850/test_ts_850.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: the visible workspace switcher trigger starts with aria-expanded="false",
changes to "true" when a mouse click opens the surface, and returns to "false"
when the second click closes it.
```

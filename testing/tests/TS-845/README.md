# TS-845

Verifies that the desktop TrackState workspace switcher trigger keeps its
`aria-expanded` state in sync with Space-key activation.

The automation:
1. launches the deployed TrackState app in Chromium with a stored hosted token
2. reaches the desktop workspace switcher trigger through a real keyboard navigation path
3. confirms the trigger exposes `aria-expanded="false"` before opening
4. presses `Space` to open the workspace switcher surface and confirms
   `aria-expanded="true"`
5. presses `Space` again to dismiss the surface and confirms
   `aria-expanded="false"`

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-845/test_ts_845.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: the focused workspace switcher trigger starts with aria-expanded="false",
changes to "true" when Space opens the surface, and returns to "false" when
Space closes it.
```

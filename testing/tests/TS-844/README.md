# TS-844 test automation

Verifies that pressing `Space` on the already-focused desktop workspace switcher
trigger closes the open workspace switcher surface and returns the trigger to its
collapsed state.

The automation:
1. launches the deployed TrackState app in Chromium with a stored hosted token
2. navigates to Dashboard and resizes to a desktop viewport
3. uses a real keyboard navigation path until the workspace switcher trigger owns
   keyboard focus
4. presses `Space` once to open the workspace switcher surface while the trigger
   keeps focus and exposes `aria-expanded="true"`
5. presses `Space` again on the same focused trigger and checks whether the
   visible surface dismisses immediately with `aria-expanded="false"`

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-844/test_ts_844.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected result

```text
Pass: after the workspace switcher surface is open and the trigger still owns
keyboard focus, pressing Space again closes the visible surface and returns the
trigger to its collapsed state with `aria-expanded="false"`.

Fail: the surface stays visible, focus leaves the trigger unexpectedly, or the
toggle interaction does not collapse the open switcher.
```

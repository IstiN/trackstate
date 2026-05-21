# TS-889

Verifies that, in the deployed desktop TrackState web app, opening the
workspace switcher moves keyboard focus off the root `FLUTTER-VIEW` element and
into the visible switcher panel once the opening transition settles.

The automation:
1. launches the deployed TrackState app in Chromium with a stored hosted token
   and two preloaded saved hosted workspaces
2. opens the desktop workspace switcher from Dashboard
3. waits for the opening transition to remain visibly settled for 1.5 seconds
4. checks the active element and verifies keyboard focus is inside the visible
   switcher panel rather than on the trigger or the root `FLUTTER-VIEW`

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-889/test_ts_889.py
```

## Required environment and config

- Python 3 with the repository test dependencies installed
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: after the desktop workspace switcher opens and its transition completes,
the active element is the panel container or an interactive child inside the
visible switcher. Focus is not left on the root FLUTTER-VIEW or the trigger.

Fail: the switcher opens but keyboard focus stays on FLUTTER-VIEW, stays on the
trigger, or otherwise does not land inside the visible switcher panel.
```

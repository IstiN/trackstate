# TS-989

Verifies that an immediate startup synchronization probe failure does not block
the deployed shell from becoming interactive.

The automation:
1. opens the deployed TrackState app in Chromium with a stored GitHub token plus
   preloaded local and hosted workspace profiles
2. aborts the first GitHub `/user` startup probe immediately to simulate the
   rejected startup handshake from the ticket
3. waits for the live page to report `shell_ready` rather than asserting
   immediately after launch
4. verifies the visible shell still exposes navigation, the top-bar workspace
   trigger, and TrackState branding instead of a crash or terminal loading
   surface

## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-989/test_ts_989.py
```

## Required environment and config

- Python 3.12+
- Playwright for Python with Chromium installed
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- Defaults come from `testing/core/config/live_setup_test_config.py`

## Expected result

```text
Pass: the initial GitHub `/user` startup probe fails immediately, but the
deployed app still reaches shell_ready within the non-blocking startup window
and shows the interactive shell with visible navigation, top-bar workspace
trigger, and TrackState branding instead of a crash screen.
```

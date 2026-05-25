# TS-1043

Validates the live startup regression case where the GitHub `/user` auth probe
must run independently of a hung secondary startup fetch.

The automation:

1. opens the deployed TrackState app with preloaded local and hosted workspace
   state
2. delays `DEMO/project.json` for 31 seconds to keep the secondary startup path
   pending
3. delays `/user` for 1 second and captures the first 5 seconds of startup
   telemetry
4. verifies `auth_probe_started` is observed within that first 5-second window
5. re-checks the timeout checkpoint after the 11-second synchronization window
   and verifies `auth_probe_released` is true while the secondary probe is still
   pending

## Install dependencies

```bash
python -m pip install -r testing/requirements.txt
playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1043/test_ts_1043.py
```

## Required configuration

- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to `api.github.com` and `istin.github.io`
- Playwright for Python with Chromium available in the environment

## Expected result

```text
Pass: the delayed startup run records `auth_probe_started` within 5 seconds, and
the later timeout checkpoint shows `auth_probe_released` while
`DEMO/project.json` is still pending.

Fail: the auth probe does not start within 5 seconds, the timeout checkpoint
cannot be sampled reliably while the secondary probe is still pending, or the
timeout checkpoint does not show `auth_probe_released`.
```

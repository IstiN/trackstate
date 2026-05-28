# TS-1002 test automation

This test validates the live TrackState startup timeout behavior for a delayed
secondary critical-path probe.

1. Preloads the deployed app with local and hosted workspace profiles plus an
   authenticated GitHub token.
2. Delays `DEMO/project.json` for 31 seconds while keeping the `/user` probe on
   a separate 1-second timing path.
3. Samples the live page from inside the browser during startup so the
   11-second timeout checkpoint is captured while the delayed secondary probe is
   still pending.
4. Verifies whether the full shell, TopBar workspace trigger, and branding are
   visible within the required timeout window.

The automation also reflects the current linked startup bug chain for this
ticket: the live app must still exercise the GitHub `/user` probe promptly, and
the global 11-second fallback must make the shell interactive even while
`DEMO/project.json` remains delayed. The linked bug set now includes TS-1145,
TS-1046, TS-1045, TS-1014, TS-1013, TS-1012, TS-996, and TS-992 for the shared
startup-timeout path, plus TS-1149 for the related fallback-session capability
surface. This test remains scoped to the visible shell behavior required by
TS-1002. If the `/user` probe is not observed and released within the early
5-second window, the test fails before evaluating the secondary-probe timeout
assertion.
## Install dependencies

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1002/test_ts_1002.py
```

## Required configuration

- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`
- network access to `https://istin.github.io/trackstate-setup/` and
  `https://api.github.com/`

## Expected output when the test passes

```text
TS-1002 passed
```

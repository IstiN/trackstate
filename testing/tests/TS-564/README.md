# TS-564 test automation

Verifies that a local release-backed attachment download without GitHub
credentials returns the fixed authentication JSON contract
(`AUTHENTICATION_FAILED` / `auth` / `3`) instead of the generic repository
error contract.

The automation:
1. reviews the ticket step `trackstate attachment download --issue TS-123 --file manual.pdf --target local --output json`
2. executes the current supported equivalent `trackstate attachment download --attachment-id TS/TS-123/attachments/manual.pdf --out ./downloads/manual.pdf --target local --output json`
3. compiles the CLI from `origin/main` so the scenario runs against the deployed auth-contract implementation even when the current branch lags behind `main`
4. seeds a disposable local TrackState repository with
   `attachmentStorage.mode = github-releases`
5. removes ambient GitHub credentials from the runtime environment
6. verifies the visible output still explains the missing GitHub auth/configuration
   problem to a user
7. inspects the JSON error `category` and `exitCode`
8. verifies no local download file is created and the repository stays clean

## Run this test

```bash
python testing/tests/TS-564/test_ts_564.py
```

## Required environment / config

- Python 3.12+
- Flutter Linux desktop tooling available on PATH
- `xvfb-run` available on PATH
- `git` CLI available on PATH
- No `GH_TOKEN`, `GITHUB_TOKEN`, or `TRACKSTATE_TOKEN` set for the test process

## Expected pass / fail behavior

- **Pass:** the local download fails with explicit GitHub auth/configuration
  guidance, the JSON error is `AUTHENTICATION_FAILED` / `auth` / `3`, and no
  local file is created.
- **Fail:** the JSON payload does not match the fixed authentication contract
  even though the visible error text mentions missing GitHub auth.

# TS-564 test automation

Verifies that a local release-backed attachment download without GitHub
credentials returns the fixed auth/configuration JSON contract instead of the
generic repository error category and exit code.

The automation:
1. reviews the ticket step `trackstate attachment download --issue TS-123 --file manual.pdf --target local --output json`
2. executes the current supported equivalent `trackstate attachment download --attachment-id TS/TS-123/attachments/manual.pdf --out ./downloads/manual.pdf --target local --output json`
3. seeds a disposable local TrackState repository with
   `attachmentStorage.mode = github-releases`
4. removes ambient GitHub credentials from the runtime environment
5. verifies the visible output still explains the missing GitHub auth/configuration
   problem to a user
6. inspects the JSON error `category` and `exitCode`
7. verifies no local download file is created and the repository stays clean

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
  guidance, the JSON error `category` is auth/config-related rather than
  `repository`, `error.exitCode` is not `4`, and no local file is created.
- **Fail:** the JSON payload still reports the generic repository category or
  exit code even though the visible error text mentions missing GitHub auth.

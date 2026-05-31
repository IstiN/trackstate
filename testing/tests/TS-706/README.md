# TS-706

Validates that the live `Apple Release Builds` workflow fails fast in its Ubuntu
preflight gate when no TrackState macOS release runner matching the configured
label contract is available.

The automation creates a disposable semantic version tag on `main`, waits for
the resulting workflow run to complete, verifies the preflight and downstream
job outcomes through the GitHub API/logs, and opens the run/job pages in
Chromium for human-style verification.

TS-706 does not rely on the repository self-hosted runners inventory API.
Instead, it treats the live workflow itself as the supported precondition
signal: the expected path is a failing preflight job with the configured
runner-availability message.

If the preflight job succeeds, the ticket precondition was not met. That
precondition-not-met outcome covers both of the live paths the automation can
observe from GitHub Actions:

- the downstream macOS job stays queued or waiting through the configured
  observation window
- the downstream macOS job proceeds and completes instead of being suppressed

## Dependencies

- GitHub CLI authenticated with repository and workflow access for
  `IstiN/trackstate`
- Playwright Python package and browser runtime for GitHub Actions page checks

## Run this test

```bash
mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-706/test_ts_706.py
```

Targeted regression coverage:

```bash
PYTHONPATH=. python3 -m unittest \
  testing.tests.TS-706.test_github_actions_preflight_gate_probe_regressions \
  testing.tests.TS-706.test_ts_706_output_regressions
```

## Config

`config.yaml` is the source of truth for:

- repository and workflow metadata
- preflight/downstream job display names
- expected Ubuntu runner and macOS label contract
- polling and UI timeout values

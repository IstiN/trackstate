# TS-557 test automation

Verifies that a local `trackstate attachment upload --target local` run fails
with an explicit missing-remote repository-identity error even when no GitHub
authentication token is present, proving identity resolution is validated before
auth/configuration guidance.

The automation:
1. creates a disposable local TrackState repository with
   `attachmentStorage.mode = github-releases`
2. leaves the local Git repository without any remotes configured
3. removes ambient GitHub credentials from the command environment
4. runs the exact ticket command against `TS-475` with a real file payload
5. checks the caller-visible CLI failure output for repository-identity guidance
   tied to missing local Git remotes
6. verifies the visible error does not prioritize generic release auth guidance
7. verifies no file was written to the local repository `attachments/` path and
   the repository stayed clean

## Install dependencies

No extra Python packages are required beyond the repository checkout. The test
compiles and runs the repo-local TrackState CLI from a disposable fixture
repository.

## Run this test

```bash
python testing/tests/TS-557/test_ts_557.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- No Git remotes configured in the seeded local repository
- No `GH_TOKEN`, `GITHUB_TOKEN`, or `TRACKSTATE_TOKEN` set for the test process

## Expected pass / fail behavior

- **Pass:** the CLI fails immediately with explicit GitHub repository-identity
  guidance explaining that local Git configuration cannot resolve the GitHub
  repository because no remote is configured, and the visible error does not
  prioritize generic release-upload authentication/configuration messaging.
- **Fail:** the command succeeds, writes a local attachment file, leaves local
  repository changes behind, or surfaces generic release-upload auth guidance
  ahead of the missing-remote repository-identity explanation.

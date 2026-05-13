# TS-523 test automation

Verifies that a local `trackstate attachment upload --target local` run fails
with explicit GitHub repository-identity guidance when the repository is
configured for `github-releases` attachments but has no Git remotes configured.

The automation:
1. creates a disposable local TrackState repository with
   `attachmentStorage.mode = github-releases`
2. leaves the local Git repository without any remotes configured
3. removes ambient GitHub credentials from the command environment
4. runs the exact ticket command against `TS-475` with a real file payload
5. checks the caller-visible CLI failure output for explicit guidance that the
   GitHub repository identity cannot be resolved from the local Git
   configuration
6. verifies no file was written to the local repository `attachments/` path and
   the repository stayed clean
7. if the exact local path only returns generic release-upload
   auth/configuration guidance, reports that as the real product gap instead of
   pretending the missing-remote contract was verified

## Install dependencies

No extra Python packages are required beyond the repository checkout. The test
compiles and runs the repo-local TrackState CLI from a disposable fixture
repository.

## Run this test

```bash
python testing/tests/TS-523/test_ts_523.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- No Git remotes configured in the seeded local repository
- No `GH_TOKEN`, `GITHUB_TOKEN`, or `TRACKSTATE_TOKEN` set for the test process
- Optional: set `TRACKSTATE_TS523_SOURCE_ROOT` to a different TrackState checkout
  (for example a temporary `origin/main` worktree) when the current branch does
  not yet contain the production fix that must be validated

## Expected pass / fail behavior

- **Pass:** the CLI fails immediately with explicit GitHub repository-identity
  guidance explaining that local Git configuration cannot resolve the GitHub
  repository for release-backed uploads, and no local attachment file is
  written under `TS/TS-475/attachments/test.txt`.
- **Fail:** the command succeeds, falls back to repository-path storage, leaves
  local repository changes behind, or returns only generic release-upload
  auth/configuration guidance without explaining the missing GitHub remote
  identity.

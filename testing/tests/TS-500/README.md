# TS-500 test automation

Verifies that a local `trackstate attachment upload --target local` run does
not silently fall back to repository-path storage when the repository is
configured for `github-releases` attachments but no GitHub authentication is
available.

The automation:
1. creates a disposable local TrackState repository with
   `attachmentStorage.mode = github-releases`
2. removes ambient GitHub credentials from the command environment
3. runs the exact ticket command against `TS-475` with a real file payload
4. checks the caller-visible CLI failure output for explicit
   release-auth/configuration guidance, whether it is surfaced via plain text,
   stderr, or a JSON-shaped error payload
5. verifies no file was written to the local repository `attachments/` path and
   the repository stayed clean

## Install dependencies

No extra Python packages are required beyond the repository checkout. The test
compiles and runs the repo-local TrackState CLI from a disposable fixture
repository.

## Run this test

```bash
python testing/tests/TS-500/test_ts_500.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- No `GH_TOKEN`, `GITHUB_TOKEN`, or `TRACKSTATE_TOKEN` set for the test process

## Expected pass / fail behavior

- **Pass:** the CLI fails immediately with explicit GitHub
  auth/configuration or GitHub Releases guidance in the visible user-facing
  output, and no local attachment file is written under
  `TS/TS-475/attachments/test.txt`.
- **Fail:** the command succeeds, falls back to repository-path storage, leaves
  local repository changes behind, or returns only a generic repository error
  instead of explicit release-auth/configuration guidance.

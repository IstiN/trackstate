# TS-560 test automation

Verifies that a local `trackstate attachment upload --target local` run fails
with a deterministic release-identity conflict when the expected GitHub Release
tag already exists but its title belongs to another issue.

The automation:
1. creates a disposable local TrackState repository configured for
   `attachmentStorage.mode = github-releases`
2. points the local Git `origin` at the live setup repository
3. ensures release `ts-attachments-TS-123` exists remotely with mismatched
   title `Attachments for TS-999`
4. runs the exact ticket command against `TS-123` with a real `report.pdf`
   payload
5. checks the caller-visible CLI failure output for the deterministic
   release-identity conflict
6. verifies no local attachment metadata or file output is written after the
   failure
7. verifies the live GitHub Release keeps the mismatched title and asset list
   after the failed command

## Install dependencies

No extra Python packages are required beyond the repository checkout. The test
compiles and runs the repo-local TrackState CLI from a disposable fixture
repository.

## Run this test

```bash
python testing/tests/TS-560/test_ts_560.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with permission to inspect and manage releases
  in `IstiN/trackstate-setup`
- Network access to the GitHub API

## Expected pass / fail behavior

- **Pass:** the CLI fails with `REPOSITORY_OPEN_FAILED`, the visible reason says
  release `ts-attachments-TS-123` does not match issue `TS-123` and requires
  manual cleanup, no local attachment files are written, and the live release
  remains unchanged.
- **Fail:** the command succeeds, uploads to the mismatched release, mutates the
  local repository, changes the live release, or returns an error that does not
  clearly describe the release-identity conflict.

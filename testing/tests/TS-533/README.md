# TS-533 test automation

Verifies that a local `trackstate attachment upload --target local` run fails
with explicit permission-denied guidance when the repository is configured for
`github-releases` attachments and the authenticated GitHub token cannot manage
releases in the resolved remote repository.

The automation:
1. creates a disposable local TrackState repository with
   `attachmentStorage.mode = github-releases`
2. points the Git remote at the public repository `octocat/Hello-World`
3. mirrors `GH_TOKEN` into `TRACKSTATE_TOKEN` for the command under test
4. runs the exact ticket command against `TS-475` with a real file payload
5. checks the caller-visible CLI failure output for explicit guidance that the
   authenticated account lacks release-management or asset-upload permission
6. verifies no file was written to the local repository `attachments/` path and
   the repository stayed clean
7. if the exact local path only returns generic release-upload
   auth/configuration guidance, reports that as the real product-visible gap

## Install dependencies

No extra Python packages are required beyond the repository checkout. The test
compiles and runs the repo-local TrackState CLI from a disposable fixture
repository.

## Run this test

```bash
python testing/tests/TS-533/test_ts_533.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- `GH_TOKEN` set to a valid GitHub token

## Expected pass / fail behavior

- **Pass:** the CLI fails immediately with explicit permission guidance such as
  requiring permission to manage releases or upload assets in the resolved
  GitHub repository, or explicitly stating that the authenticated GitHub
  identity does not permit GitHub Release uploads there, and no local
  attachment file is written under
  `TS/TS-475/attachments/test.txt`.
- **Fail:** the command succeeds, falls back to repository-path storage, leaves
  local repository changes behind, or returns only generic
  auth/configuration guidance without explaining the permission problem.

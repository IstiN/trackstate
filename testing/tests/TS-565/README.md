# TS-565 test automation

Verifies that local release-backed attachment download validation checks
repository identity before authentication state when the local Git repository
has no remotes configured.

The automation:
1. seeds a disposable local TrackState repository with
   `attachmentStorage.mode = github-releases`
2. writes `attachments.json` with a release-backed `manual.pdf` entry for
   `TS/TS-123/attachments/manual.pdf`
3. ensures the local Git repository has no remotes and strips ambient GitHub
   credentials from the command environment
4. runs `trackstate attachment download --attachment-id
   TS/TS-123/attachments/manual.pdf --out ./downloads/manual.pdf --target local`
5. verifies the caller-visible CLI failure names the missing-remote repository
   identity problem before any authentication guidance
6. verifies no local output file is created, the full `attachments.json`
   manifest text stays unchanged, and the disposable repository remains clean

## Install dependencies

No extra Python packages are required beyond the repository checkout. The test
compiles and runs the repo-local TrackState CLI from a disposable fixture
repository.

## Run this test

```bash
python testing/tests/TS-565/test_ts_565.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- No `GH_TOKEN`, `GITHUB_TOKEN`, or `TRACKSTATE_TOKEN` set for the test process

## Expected result

- **Pass:** the CLI fails immediately with explicit GitHub repository-identity
  guidance explaining that no remote is configured, no `downloads/manual.pdf`
  file is created, and the full `attachments.json` manifest remains unchanged.
- **Fail:** the command succeeds, creates a local output file, mutates any part
  of `attachments.json`, leaves repository changes behind, or surfaces provider
  / authentication guidance before the missing-remote identity error.

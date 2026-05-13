# TS-522 test automation

Verifies that a local `trackstate attachment download --target local` run does
not silently fall through with a generic repository/provider failure when the
repository is configured for `github-releases` attachments but no GitHub
authentication is available.

The ticket targets behavior that is already fixed on `main`, so this automation
compiles the CLI from `origin/main` before exercising the disposable local
fixture repository. That keeps TS-522 aligned with the deployed implementation
even when the current branch predates the production fix.

The automation:
1. seeds a disposable local TrackState repository with
   `attachmentStorage.mode = github-releases`
2. writes `attachments.json` with a release-backed `manual.pdf` entry for
   `TS/TS-123/attachments/manual.pdf`
3. removes ambient GitHub credentials from the command environment
4. runs `trackstate attachment download --attachment-id
   TS/TS-123/attachments/manual.pdf --out ./downloads/manual.pdf --target local`
5. checks the caller-visible CLI failure output for explicit GitHub
   Releases/auth/configuration guidance, whether surfaced via plain text,
   stderr, or a JSON-shaped error payload
6. verifies no local output file is created and the disposable repository stays
   clean
7. if the exact local path still fails earlier at the provider capability gate,
   reports that as the real product gap instead of pretending the missing-auth
   contract was verified

## Install dependencies

No extra Python packages are required beyond the repository checkout. The test
compiles and runs the repo-local TrackState CLI from a disposable fixture
repository.

## Run this test

```bash
python testing/tests/TS-522/test_ts_522.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- No `GH_TOKEN`, `GITHUB_TOKEN`, or `TRACKSTATE_TOKEN` set for the test process

## Expected pass / fail behavior

- **Pass:** the CLI compiled from `origin/main` fails immediately with explicit GitHub
  auth/configuration or GitHub Releases guidance for the release-backed
  attachment download, and no `downloads/manual.pdf` file is created.
- **Fail:** the command succeeds, writes a local output file, leaves repository
  changes behind, returns only a generic repository/provider error, or hits the
  current local-provider capability gate (`This repository provider does not
  support GitHub Releases attachment downloads.`) before auth is consulted.

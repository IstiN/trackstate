# TS-535 test automation

Verifies that a local release-backed `trackstate attachment download --target local`
run returns explicit missing-asset guidance when the attachment manifest points at a
real GitHub Release that exists but does not contain the requested asset.

The automation:
1. creates a disposable local TrackState repository whose `attachments.json`
   contains `TS/TS-123/attachments/manual.pdf` backed by GitHub Releases
2. exports the repository `main` branch to a temporary snapshot and compiles the
   TrackState CLI from that tree so the probe exercises the deployed
   implementation instead of the stale test branch checkout
3. points the fixture repository `origin` at `https://github.com/cli/cli.git`
   and references public release tag `v2.74.0`
4. removes ambient GitHub credentials from the command environment
5. runs the supported local CLI form
   `trackstate attachment download --attachment-id TS/TS-123/attachments/manual.pdf --out ./downloads/manual.pdf --target local`
6. checks the caller-visible CLI failure output for explicit guidance that the
   remote release does not contain `manual.pdf`
7. verifies no output file is created under `downloads/manual.pdf` and the local
   repository stays clean
8. if the local provider still fails earlier at the GitHub Releases capability
   gate, reports that as the real product gap instead of pretending the
   missing-asset contract was verified

## Install dependencies

No extra Python packages are required beyond the repository checkout. The test
compiles and runs the repo-local TrackState CLI from a disposable fixture
repository.

## Run this test

```bash
python testing/tests/TS-535/test_ts_535.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- Network access to read the public GitHub release metadata for `cli/cli` tag
  `v2.74.0`
- No `GH_TOKEN`, `GITHUB_TOKEN`, or `TRACKSTATE_TOKEN` set for the test process

## Expected pass / fail behavior

- **Pass:** the CLI fails with explicit missing-asset guidance explaining that
  GitHub release `v2.74.0` does not contain `manual.pdf`, and no file is
  written under `downloads/manual.pdf`.
- **Fail:** the command succeeds, creates a local output file, leaves repository
  changes behind, or only reports the generic local-provider GitHub Releases
  capability error instead of the missing-asset contract.

# TS-540 test automation

Verifies that a local-git `trackstate attachment download --target local` request
can download a release-backed attachment successfully when the attachment manifest
entry uses `storageBackend = github-releases`.

The automation:
1. creates a real GitHub Release fixture in the live setup repository and uploads
   `manual.pdf`
2. seeds a disposable local TrackState repository whose `attachments.json`
   references that release tag and asset name
3. runs the supported local CLI form
   `trackstate attachment download --attachment-id TS/TS-123/attachments/manual.pdf --out ./downloads/manual.pdf --target local`
4. verifies the visible JSON response reports a successful local-git
   attachment-download result
5. verifies `downloads/manual.pdf` is created and its bytes exactly match the
   uploaded GitHub Release asset

## Install dependencies

No extra Python packages are required beyond the repository checkout. The test
compiles and runs the repo-local TrackState CLI from a disposable fixture
repository.

## Run this test

```bash
python testing/tests/TS-540/test_ts_540.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with permission to create releases and upload
  assets in the live setup repository
- Network access to GitHub Releases for the configured live setup repository

## Expected pass / fail behavior

- **Pass:** the CLI bypasses the local provider capability gate, returns a JSON
  success envelope for the local-git attachment download, writes
  `downloads/manual.pdf`, and the saved bytes match the uploaded release asset.
- **Fail:** the command exits non-zero, still reports the generic provider
  capability error, omits required success metadata, fails to create the output
  file, or writes bytes that differ from the uploaded release asset.

# TS-594 test automation

Verifies that a local `trackstate attachment download --target local --output json`
request can retrieve a release-backed attachment successfully when the repository
has a valid GitHub remote and valid authentication is available.

The automation:
1. creates a real GitHub Release fixture in the live setup repository and uploads
   `manual.pdf`
2. seeds a disposable local TrackState repository whose `attachments.json`
   references that release tag and asset name
3. runs the supported local CLI form
   `trackstate attachment download --attachment-id TS/TS-123/attachments/manual.pdf --out ./downloads/manual.pdf --target local --output json`
4. verifies the visible JSON response reports a successful `local-git`
   attachment-download result
5. verifies `downloads/manual.pdf` is created and contains the expected fixture
   text from the uploaded GitHub Release asset

## Prerequisites

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- `TRACKSTATE_TOKEN`, `GH_TOKEN`, or `GITHUB_TOKEN` with permission to create
  releases and upload assets in the live setup repository
- Network access to GitHub Releases for the configured live setup repository

## Run this test

```bash
python testing/tests/TS-594/test_ts_594.py
```

# TS-553 test automation

Validates that a local `trackstate attachment upload --target local` run replaces
an existing GitHub Release asset deterministically when the same filename is
uploaded again for the same issue.

The automation:
1. creates a disposable local TrackState repository configured for
   `attachmentStorage.mode = github-releases`
2. points the local Git remote at the live setup repository
3. pre-seeds the issue release container with one `doc.pdf` asset and writes a
   matching `attachments.json` entry
4. runs the exact ticket command `trackstate attachment upload --issue TS-123 --file doc.pdf --target local`
5. verifies the live GitHub Release still contains exactly one `doc.pdf` asset
   whose bytes match the replacement payload
6. verifies local `attachments.json` now points at the new asset identifier

## Run this test

```bash
python testing/tests/TS-553/test_ts_553.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- `gh` CLI available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with release upload access to the hosted setup
  repository

## Expected pass / fail behavior

- **Pass:** the CLI succeeds, local `attachments.json` updates from the seeded
  asset id to the new asset id, and the live GitHub Release exposes exactly one
  `doc.pdf` asset whose downloaded bytes match the replacement payload.
- **Fail:** the CLI fails, leaves duplicate `doc.pdf` assets, keeps the old
  asset identifier in `attachments.json`, or serves the stale seeded bytes
  after the replacement upload.

# TS-610 test automation

Validates that a local `trackstate attachment upload --target local` run performs
the GitHub Release replacement flow in the correct API order when the uploaded
filename already exists in the issue release container.

The automation:
1. creates a disposable local TrackState repository configured for
   `attachmentStorage.mode = github-releases`
2. points the local Git remote at the live setup repository
3. pre-seeds the issue release container with one `logic.drawio` asset and writes
   a matching `attachments.json` entry
4. runs the exact ticket command
   `trackstate attachment upload --issue TS-123 --file logic.drawio --target local`
5. captures the live GitHub API request flow made by the CLI harness
6. verifies the CLI performs `GET /releases/tags/{tag}` before
   `DELETE /releases/assets/{asset_id}` and only uploads the new bytes with
   `POST uploads.github.com/.../assets?name=logic.drawio` afterward
7. verifies the live GitHub Release still contains exactly one `logic.drawio`
   asset whose bytes match the replacement payload
8. verifies local `attachments.json` now points at the new asset identifier

## Run this test

```bash
python3 testing/tests/TS-610/test_ts_610.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with release upload access to the hosted setup
  repository

## Expected pass / fail behavior

- **Pass:** the CLI succeeds, the request flow shows release lookup before asset
  deletion before upload, local `attachments.json` updates to the new asset id,
  and the live GitHub Release exposes exactly one `logic.drawio` asset whose
  downloaded bytes match the replacement payload.
- **Fail:** the lookup/delete/upload order is wrong or incomplete, the CLI
  duplicates the asset, keeps the old asset identifier in `attachments.json`, or
  serves the stale seeded bytes after the replacement upload.

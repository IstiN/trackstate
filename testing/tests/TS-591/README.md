# TS-591 test automation

Verifies that a local `trackstate attachment upload --target local` replacement
fails explicitly when the GitHub Release asset delete step returns HTTP 403, and
that the existing `attachments.json` manifest entry remains unchanged.

The automation:
1. creates a disposable local TrackState repository configured with
   `attachmentStorage.mode = github-releases`
2. points the local Git remote at the live setup repository
3. seeds the issue release container with an existing `data.csv` asset and a
   matching local `attachments.json` entry for `TS-123`
4. forces only `DELETE /repos/{owner}/{repo}/releases/assets/{asset_id}` to
   return HTTP 403 through the test-only CLI harness override
5. runs the exact ticket command
   `trackstate attachment upload --issue TS-123 --file data.csv --target local`
6. verifies the caller-visible CLI output reports the replacement delete failure
7. verifies the local manifest and live release asset id still point to the
   original seeded `data.csv` asset

## Run this test

```bash
python testing/tests/TS-591/test_ts_591.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with release upload access to the hosted setup
  repository

## Expected pass / fail behavior

- **Pass:** the CLI fails with an explicit GitHub Release asset replacement
  error after the delete step returns HTTP 403, `attachments.json` still
  references the original asset id, and the live release still exposes the
  seeded `data.csv` asset.
- **Fail:** the command succeeds, the visible error hides the replacement delete
  failure, the manifest changes to a new asset id, or the live release no
  longer reflects the original seeded asset.

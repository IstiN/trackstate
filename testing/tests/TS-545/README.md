# TS-545 test automation

Validates that a local `trackstate attachment upload --target local` run succeeds
when the repository uses `attachmentStorage.mode = github-releases` and a valid
GitHub remote origin is configured.

The automation:
1. creates a disposable local TrackState repository configured for
   `attachmentStorage.mode = github-releases`
2. points the local Git remote at the live setup repository
3. uploads `test-upload.txt` to `TS-100` with the real CLI command
4. checks the local `attachments.json` metadata for the uploaded release asset
5. checks the live GitHub Release and `gh release view` output for
   `test-upload.txt`

## Run this test

```bash
python testing/tests/TS-545/test_ts_545.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- `gh` CLI available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with release upload access to the live setup
  repository

## Expected pass / fail behavior

- **Pass:** the CLI succeeds without `REPOSITORY_OPEN_FAILED`, local
  `attachments.json` records `githubReleaseAssetName = test-upload.txt`, and the
  live GitHub Release exposes `test-upload.txt`.
- **Fail:** the CLI still fails through the local capability gate, the upload
  does not create the release-backed metadata, or `gh release view` does not
  show the uploaded asset.

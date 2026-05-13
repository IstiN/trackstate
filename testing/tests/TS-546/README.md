# TS-546 test automation

Validates that a local `trackstate attachment upload --target local` run uploads
a filename with special characters to GitHub Releases using the repository's
attachment-name sanitization rules.

This ticket uses the shared release-asset sanitization support flow under
`testing/tests/support/`, while keeping TS-546 isolated with its own config,
release tag prefix, and reporting entrypoint.

The automation:
1. creates a disposable local TrackState repository configured for
   `attachmentStorage.mode = github-releases`
2. points the local Git remote at the live setup repository
3. uploads `Report #2026 (Final)!.pdf` to `TS-100` with the real CLI command
4. checks the local `attachments.json` metadata for the sanitized
   `githubReleaseAssetName`
5. checks the live GitHub Release and `gh release view` output for the same
   sanitized asset name

## Run this test

```bash
python testing/tests/TS-546/test_ts_546.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- `gh` CLI available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with release upload access to the live setup
  repository

## Expected pass / fail behavior

- **Pass:** the CLI succeeds, the local attachment manifest records
  `githubReleaseAssetName = Report-2026-Final-.pdf`, and the live GitHub
  Release exposes exactly that sanitized asset name.
- **Fail:** the CLI fails, stores the raw unsanitized asset name, creates the
  wrong release asset, or `gh release view` does not show the sanitized asset.

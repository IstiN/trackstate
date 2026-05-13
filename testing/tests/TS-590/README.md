# TS-590 test automation

Verifies that a local `trackstate attachment upload --target local` run reuses an
existing matching GitHub Release and normalizes its manually edited body back to
the standard TrackState machine-managed note.

The automation:
1. creates a disposable local TrackState repository configured for
   `attachmentStorage.mode = github-releases`
2. points the local Git remote at the live setup repository
3. seeds a matching draft release for `TS-123` with the correct tag/title but a
   custom non-standard body
4. runs the exact ticket command `trackstate attachment upload --issue TS-123 --file note.txt --target local`
5. verifies local `attachments.json` converges to the expected release-backed
   entry
6. verifies the same seeded release id is reused and its body becomes
   `TrackState-managed attachment container for TS-123.\n`
7. verifies `gh release view` shows the normalized body and uploaded asset

## Run this test

```bash
python testing/tests/TS-590/test_ts_590.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- `gh` CLI available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with release upload access to the hosted setup
  repository

## Expected pass / fail behavior

- **Pass:** the CLI succeeds, local `attachments.json` records the
  release-backed entry for `note.txt`, the seeded release id is reused, and both
  the live GitHub API state and `gh release view` show the standard
  machine-managed body.
- **Fail:** the CLI fails, creates a different release, leaves the custom body
  unchanged, or shows a body other than the standard machine-managed note after
  the upload.

# TS-552 test automation

Verifies that a local `github-releases` attachment upload fails with a visible
asset-container conflict when the target GitHub Release already contains a
foreign asset that is not tracked in `attachments.json`.

The automation:
1. creates a disposable local TrackState repository configured with
   `attachmentStorage.mode = github-releases`
2. points the local Git `origin` at the live setup repository
3. seeds a real GitHub Release for `TS-123` with the correct tag/title plus a
   foreign `foreign-file.zip` asset while local `attachments.json` stays empty
4. runs the exact ticket command
   `trackstate attachment upload --issue TS-123 --file report.pdf --target local`
5. verifies the user-visible CLI output reports the foreign-asset/manual-cleanup
   conflict
6. verifies the local manifest stays unchanged and the release still exposes only
   `foreign-file.zip`

## Run this test

```bash
python testing/tests/TS-552/test_ts_552.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- `gh` CLI available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected pass / fail behavior

- **Pass:** the command fails with the expected foreign-asset conflict, names
  `foreign-file.zip`, requires manual cleanup, leaves local `attachments.json`
  untouched, and does not add `report.pdf` to the live release.
- **Fail:** the command succeeds, reports the wrong failure, mutates local
  attachment metadata, deletes/absorbs the foreign asset, or cannot exercise the
  production-visible local Git + GitHub Releases flow.

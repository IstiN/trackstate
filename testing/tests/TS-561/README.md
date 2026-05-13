# TS-561 test automation

Verifies that a local `github-releases` attachment upload fails with an
asset-container conflict when the target GitHub Release already contains a
foreign asset that is not tracked in `attachments.json`.

The automation:
1. creates a disposable local TrackState repository configured with
   `attachmentStorage.mode = github-releases`
2. points the local Git `origin` at the live setup repository
3. seeds a real GitHub Release for `TS-123` with the foreign
   `external-file.zip` asset while local `attachments.json` stays empty
4. runs the exact ticket command
   `trackstate attachment upload --issue TS-123 --file trackstate-file.txt --target local`
5. verifies the user-visible CLI output reports the foreign-asset conflict
6. verifies the local manifest stays unchanged and the release still exposes
   only `external-file.zip`

## Install dependencies

```bash
dart pub get
gh auth status
```

No additional Python package installation is required in this repository
checkout; the test uses the existing Python environment plus the repository's
Dart dependencies.

## Run this test

```bash
python testing/tests/TS-561/test_ts_561.py
```

## Required environment / config

- Python 3.12+
- Dart SDK available on `PATH` or via `TRACKSTATE_DART_BIN`
- `git` CLI available on `PATH`
- `gh` CLI available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with access to `IstiN/trackstate-setup`

## Expected output when the test passes

- The command fails with a visible conflict that names `external-file.zip`
- The output indicates the release contains unexpected assets and requires
  manual cleanup
- Local `TS/TS-123/attachments.json` remains `[]`
- The live GitHub Release still exposes only `external-file.zip`

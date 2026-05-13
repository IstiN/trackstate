# TS-485

Validates mixed attachment backend resolution from the production CLI metadata
manifest when a project has switched from legacy repository-path storage to
`github-releases`.

The automation:
1. seeds a disposable local TrackState repository with issue `TS-10`
2. preserves a legacy `old.pdf` entry in `TS/TS-10/attachments.json` with
   `storageBackend = repository-path`
3. switches `TS/project.json` to `attachmentStorage.mode = github-releases`
   using a unique release tag prefix and a live GitHub `origin`
4. runs the exact ticket upload command for `new.png` with GitHub credentials
   injected into the disposable local CLI environment
5. checks the observable manifest before and after the upload attempt
6. runs the exact ticket download command for the legacy `old.pdf` attachment
7. deletes the temporary GitHub Release created for the upload

## Run this test

```bash
python3 testing/tests/TS-485/test_ts_485.py
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have:

- a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN` must point to the
  Dart executable used to compile the temporary TrackState CLI
- the `git` CLI available on `PATH`
- `GH_TOKEN` or `GITHUB_TOKEN` with release upload access to the live setup
  repository so the local `github-releases` upload path can authenticate

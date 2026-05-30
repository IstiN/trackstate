# TS-1213

Validates that a standard non-hierarchical link operation removes stale legacy
issue-local `links.json` metadata and consolidates the live link record at the
repository root.

The automation:
1. seeds a disposable local Git-backed TrackState repository with one existing
   issue so local mutations can open the repository
2. runs the live `trackstate ticket create` flow to create the source story
3. manually seeds a legacy `TS/TS-1/links.json` artifact to model pre-existing
   old metadata in the issue directory
4. creates the target story with the live CLI
5. links the two issues with `trackstate ticket link --type blocks`
6. confirms the repository-root `links.json` file contains the expected live
   non-hierarchical link record and that `TS/TS-1/links.json` has been removed

## Run this test

```bash
PYTHONPATH=. python3 testing/tests/TS-1213/test_ts_1213.py
```

## Required configuration

No external credentials are required. The repository under test must have:

- a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN` must point to the
  Dart executable used by the generated CLI harness
- the `git` CLI available on `PATH`

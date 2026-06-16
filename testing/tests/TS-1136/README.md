# TS-1136

Validates that non-hierarchical link metadata is persisted only in the
repository-root `links.json` artifact and is not duplicated inside individual
issue directories by the production local CLI.

The automation:
1. seeds a disposable local Git-backed TrackState repository with one existing
   issue so local mutations can open the repository
2. runs the live `trackstate ticket create` flow twice to create two separate
   story issues
3. links those issues with `trackstate ticket link --type blocks`
4. inspects the repository-root `links.json` file and confirms it contains the
   expected non-hierarchical link record
5. inspects both issue directories and confirms they still expose their
   `main.md` issue artifact without creating redundant `links.json` files

## Run this test

```bash
PYTHONPATH=. python3 testing/tests/TS-1136/test_ts_1136.py
```

## Required configuration

No external credentials are required. The repository under test must have:

- a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN` must point to the
  Dart executable used by the generated CLI harness
- the `git` CLI available on `PATH`

# TS-602

Validates that hierarchical parent-child relationships stay out of
`links.json`, while non-hierarchical links are still persisted correctly by the
production local CLI.

The automation:
1. seeds a disposable local Git-backed TrackState repository with one existing
   issue so local mutations can open the repository
2. runs the live `trackstate ticket create` flow to create a parent story
3. runs the live `trackstate ticket create --parent TS-1` flow to create a
   sub-task under that story
4. creates two unrelated stories and links them with
   `trackstate ticket link --type blocks`
5. inspects the repository-root `links.json` file and confirms it contains only
   the non-hierarchical link record
6. confirms the child markdown plus local issue index still show the canonical
   `parent: TS-1` relationship rather than persisting hierarchy metadata as a
   non-hierarchical link

## Run this test

```bash
PYTHONPATH=. python3 testing/tests/TS-602/test_ts_602.py
```

## Required configuration

No external credentials are required. The repository under test must have:

- a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN` must point to the
  Dart executable used by the generated CLI harness
- the `git` CLI available on `PATH`

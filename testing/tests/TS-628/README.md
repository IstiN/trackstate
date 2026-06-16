# TS-628

Reproduces the local CLI inverse-link normalization scenario for the
non-hierarchical `is cloned by` label.

The automation:
1. seeds a disposable local TrackState repository with one existing issue
2. creates Issue A (`TS-1`) and Issue B (`TS-2`) through the real CLI
3. runs `trackstate ticket link --type "is cloned by"` from Issue A to Issue B
4. verifies the CLI response reports the visible link operation details
5. checks the repository stores exactly one canonical `clones` relation from
   Issue B back to Issue A in `links.json`

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-628 -p 'test_ts_628.py' -v
```

## Required configuration

No Python packages are required beyond the standard library and the repository's
existing test dependencies. The repository under test must have:

- a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN` must point to the
  Dart executable used by the local CLI harness
- the `git` CLI available on `PATH`

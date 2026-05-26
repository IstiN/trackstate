# TS-379

Verifies that the CLI read-command compatibility aliases return the same raw
Jira-shaped JSON payloads as the canonical `trackstate read ...` commands for
ticket, field, and status metadata reads.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-379 -p 'test_*.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to compile the temporary TrackState CLI.

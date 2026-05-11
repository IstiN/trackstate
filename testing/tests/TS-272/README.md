# TS-272

Verifies that the live `trackstate session` command defaults to JSON output and
returns the versioned TrackState success envelope when run against a valid Local
Git repository fixture.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-272 -p 'test_*.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to run `dart run trackstate`. The probe
always executes the CLI from this checkout via `dart run trackstate` so it
cannot validate an unrelated standalone `trackstate` binary from `PATH`.

## Expected passing output

```text
test_session_defaults_to_json_success_envelope (test_ts_272.TrackStateCliSessionContractTest.test_session_defaults_to_json_success_envelope) ... ok

----------------------------------------------------------------------
Ran 1 test in <time>

OK
```

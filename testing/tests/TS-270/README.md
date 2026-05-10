# TS-270

Verifies that the live `trackstate session --target local` command returns the
documented machine-readable repository error contract when it is launched from a
directory that is not a Git repository.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-270 -p 'test_*.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable. When a standalone `trackstate` binary is not
installed on `PATH`, the probe compiles a temporary executable from this
checkout so it can still execute the CLI from a non-repository working
directory.

## Expected passing output

```text
test_invalid_local_target_reports_repository_open_failed (test_ts_270.LocalTargetValidationCliContractTest.test_invalid_local_target_reports_repository_open_failed) ... ok

----------------------------------------------------------------------
Ran 1 test in <time>

OK
```

# TS-269

Verifies that the live `trackstate --target local` command defaults the local
target to the current working directory when it is executed from inside a valid
TrackState/git repository and no `--path` argument is provided.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-269 -p 'test_*.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to compile a temporary TrackState CLI
binary from this checkout. The probe seeds a disposable Local Git repository,
compiles a repository-pinned executable, and runs `trackstate --target local`
from that repository working directory so it can verify the current-working-
directory default.

## Expected passing output

```text
test_local_target_defaults_to_current_working_directory (test_ts_269.LocalTargetDefaultsToCurrentWorkingDirectoryTest.test_local_target_defaults_to_current_working_directory) ... ok
test_run_from_repository_cwd_without_path_argument (test_trackstate_cli_local_target_default_framework.TrackStateCliLocalTargetDefaultFrameworkRegressionTest.test_run_from_repository_cwd_without_path_argument) ... ok

----------------------------------------------------------------------
Ran 2 tests in <time>

OK
```

## Expected failing output for a live product defect

If the product behavior regresses, `test_ts_269.py` fails with the captured
command output from the seeded repository run, showing the exact CLI error that
prevented `trackstate --target local` from resolving the current working
directory.

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
must point to the Dart executable used to run the repository-local CLI entry
point. The probe seeds a disposable Local Git repository and executes
`dart <repo>/bin/trackstate.dart --target local` from that repository working
directory so it can verify the current-working-directory default.

## Expected passing output

```text
test_local_target_defaults_to_current_working_directory (test_ts_269.LocalTargetDefaultsToCurrentWorkingDirectoryTest.test_local_target_defaults_to_current_working_directory) ... ok
test_run_from_repository_cwd_without_path_argument (test_trackstate_cli_local_target_default_framework.TrackStateCliLocalTargetDefaultFrameworkRegressionTest.test_run_from_repository_cwd_without_path_argument) ... ok

----------------------------------------------------------------------
Ran 2 tests in <time>

OK
```

## Expected failing output for the current product defect

If the product bug is still present, `test_ts_269.py` fails because the root CLI
treats `--target` as an unknown command instead of proceeding successfully from
the current repository.

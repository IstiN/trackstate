# TS-274

Verifies that the live `trackstate --help` output documents the stable
target-selection options exposed by the CLI story and shows the minimal local
and hosted usage examples users need to discover the feature.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-274 -p 'test_*.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to run `dart run trackstate`.

## Expected passing output

```text
test_root_help_documents_target_selection_and_examples (test_ts_274.TrackStateCliHelpDiscoverabilityTest.test_root_help_documents_target_selection_and_examples) ... ok

----------------------------------------------------------------------
Ran 1 test in <time>

OK
```

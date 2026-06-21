# TS-1373

Regression test for [TS-1371] verifying that a local-target CLI session reports
`authSource: "none"` even when ambient GitHub CLI tokens (`GH_TOKEN`,
`GITHUB_TOKEN`) are present in the environment.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-1373 -p 'test_*.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to run `dart run trackstate`.

## Expected passing output

```text
test_local_target_ignores_ambient_github_tokens (test_ts_1373.TrackStateLocalAuthSourceRegressionTest.test_local_target_ignores_ambient_github_tokens) ... ok

----------------------------------------------------------------------
Ran 1 test in <time>

OK
```

# TS-385

Verifies that the live `trackstate jira_execute_request` fallback rejects the
unsafe binary-flow and admin-path requests from TS-385 before local repository
access.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-385 -p 'test_*.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to run `dart run trackstate`. The probe
always executes the CLI from this checkout and passes an empty temporary
directory through `--path` so package resolution succeeds while any premature
local repository access remains visible in the JSON error contract.

## Expected passing output

```text
test_cli_rejects_binary_and_admin_fallback_requests_before_repo_access (test_ts_385.TrackStateCliFallbackBoundariesTest.test_cli_rejects_binary_and_admin_fallback_requests_before_repo_access) ... ok

----------------------------------------------------------------------
Ran 1 test in <time>

OK
```

## Expected failing output for the current product defect

If the product bug is still present, this test fails because
`jira_execute_request` reaches local repository resolution before it rejects the
unsupported fallback request, so the CLI returns a repository/validation error
contract instead of `UNSUPPORTED_REQUEST`.

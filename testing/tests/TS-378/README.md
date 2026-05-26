# TS-378

Verifies that the exact ticket command `trackstate read account-by-email
user@example.com` returns an explicit unsupported CLI error contract instead of
attempting repository-backed resolution.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-378 -p 'test_*.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to run `dart run trackstate`.

## Expected passing output

```text
test_cli_reports_account_by_email_as_explicitly_unsupported (test_ts_378.AccountByEmailUnsupportedCliContractTest.test_cli_reports_account_by_email_as_explicitly_unsupported) ... ok

----------------------------------------------------------------------
Ran 1 test in <time>

OK
```

## Expected failing output for the current product defect

If the product bug is still present, this test fails because the exact ticket
command returns a repository-open failure contract instead of an explicit
unsupported error for the account-by-email operation.

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
under test must have Flutter available on `PATH` so the temporary CLI harness
can be compiled from the current checkout.

## Expected passing output

```text
test_cli_reports_account_by_email_as_explicitly_unsupported (test_ts_378.AccountByEmailUnsupportedCliContractTest.test_cli_reports_account_by_email_as_explicitly_unsupported) ... ok

----------------------------------------------------------------------
Ran 1 test in <time>

OK
```

## Expected failing output for a regression

If the product regresses, this test fails because the exact ticket command no
longer returns the explicit unsupported error contract from a seeded Local Git
repository.

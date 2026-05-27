# TS-377

Verifies that `trackstate read profile --target local` returns a Jira-shaped
user object derived from the active Local Git identity in a disposable
repository fixture.

The automation:
1. seeds a disposable Local Git repository with `user.name = John Doe` and
   `user.email = john@example.com`
2. compiles a temporary `trackstate` executable from this checkout
3. runs the exact ticket command from the seeded repository
4. verifies the returned JSON exposes `displayName`, `emailAddress`, and
   `accountId` mapped from the Local Git identity

## Run this test

```bash
python -m unittest testing.tests.TS-377.test_ts_377
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to compile the CLI. The `git` CLI must
also be available on `PATH` so the disposable Local Git repository can be
seeded.

## Expected passing output

```text
.
----------------------------------------------------------------------
Ran 1 test in <time>

OK
```

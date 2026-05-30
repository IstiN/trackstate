# TS-1235

Validates that `trackstate ticket update` accepts a JSON array inside repeated
`--field` arguments without fragmenting the value on commas.

The automation:

1. seeds a disposable Local Git repository with `TS/TS-1/main.md`,
2. runs the live `trackstate ticket update --target local --key TS-1 --field
   summary=... --field priority=... --field labels=[...] --field assignee=...`
   flow through the repository checkout,
3. verifies the CLI returns a JSON success envelope instead of
   `INVALID_ARGUMENT`,
4. checks `TS/TS-1/main.md` visibly stores `labels: ["bug","ai"]` and the new
   summary, and
5. confirms all field changes persist in exactly one commit with a clean
   worktree.

## Install dependencies

No additional Python packages are required beyond the standard library.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-1235 -p 'test_*.py' -v
```

## Required configuration

The repository under test must have a Dart SDK available on `PATH`, or
`TRACKSTATE_DART_BIN` must point to the Dart executable used to run
`dart run trackstate`.

## Expected passing output

`unittest` reports one passing test:

```text
Ran 1 test in <time>

OK
```

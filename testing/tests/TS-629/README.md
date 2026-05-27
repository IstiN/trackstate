# TS-629

Validates that the local CLI response payload rewrites the inverse
`is blocked by` label into canonical relationship metadata for the user-visible
JSON output.

The automation:
1. seeds a disposable Local Git TrackState repository with one existing issue
2. creates Issue A (`TS-1`) and Issue B (`TS-2`) through the real CLI
3. runs `trackstate ticket link --type "is blocked by"` from Issue A to Issue B
4. inspects the returned JSON payload from the visible CLI response
5. verifies the response reports the canonical relationship metadata:
   `{"type":"blocks","target":"TS-1","direction":"outward"}`

## Install dependencies

No Python packages are required beyond the standard library and the repository's
existing test dependencies.

The test requires:
- a Flutter SDK available on `PATH`, because the repository-local compiled CLI
  harness runs through `flutter test`
- the `git` CLI available on `PATH`

## Run this test

```bash
python -m unittest testing.tests.TS-629.test_ts_629
```

## Environment variables

No ticket-specific environment variables are required.

## Expected passing output

```text
.
----------------------------------------------------------------------
Ran 1 test in <time>

OK
```

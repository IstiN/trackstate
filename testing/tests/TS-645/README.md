# TS-645

Validates that the local CLI returns a controlled JSON error envelope when a
user supplies an unsupported issue link label.

The automation:
1. seeds a disposable Local Git TrackState repository with one existing issue
2. creates Issue A (`TS-1`) and Issue B (`TS-2`) through the real CLI
3. runs `trackstate ticket link --type "unsupported_link_type_label"` from
   Issue A to Issue B
4. inspects the returned JSON response from the visible CLI output
5. verifies the response reports `ok: false` with the validation error message
   `Unsupported link type unsupported_link_type_label.`

## Install dependencies

No Python packages are required beyond the standard library and the repository's
existing test dependencies.

The test requires:
- a Flutter SDK available on `PATH`, because the repository-local compiled CLI
  harness runs through `flutter test`
- the `git` CLI available on `PATH`

## Run this test

```bash
python -m unittest discover -s testing/tests/TS-645 -p 'test_ts_645.py'
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

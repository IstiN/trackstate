# TS-648

Validates that the Jira-compatible `jira-link-issues` CLI entry point returns
canonical relationship metadata in its visible JSON response payload.

The automation:
1. seeds a disposable Local Git TrackState repository with one existing issue
2. creates Issue A (`TS-1`) and Issue B (`TS-2`) through the real CLI
3. runs `trackstate jira-link-issues --key TS-1 --target-key TS-2 --type "is blocked by"`
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
python -m unittest discover -s testing/tests/TS-648 -p 'test_ts_648.py'
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

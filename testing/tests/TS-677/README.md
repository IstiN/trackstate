# TS-677

Verifies that `trackstate read ticket --key TS-10` handles an issue with no
relationships without throwing mapping errors and without inventing link data.

The automation:
1. compiles a temporary repository-local `trackstate` executable from this checkout
2. seeds a disposable Local Git TrackState repository with issue `TS-10`
3. runs the exact ticket step `trackstate read ticket --key TS-10`
4. checks the parsed JSON root exposes a raw Jira issue object
5. verifies `fields.issuelinks` is an empty array and the top-level `links`
   property is either absent or `[]`
6. confirms the terminal-visible output shows the clean issue content without
   any relationship entries

## Install dependencies

No additional Python packages are required beyond the standard library and the
repository's existing test dependencies.

The test requires:
- a Flutter SDK available on `PATH`, because the repository-local compiled CLI
  harness runs through `flutter test`
- the `git` CLI available on `PATH`

## Run this test

```bash
python -m unittest testing.tests.TS-677.test_ts_677
```

## Environment variables

No ticket-specific environment variables are required.

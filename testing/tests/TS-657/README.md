# TS-657

Reproduces the requested local CLI scenario for viewing the target side of a
symmetric `relates to` link.

The automation:
1. seeds a disposable Local Git TrackState repository with one existing issue
2. creates Issue A (`TS-1`) and Issue B (`TS-2`) through the real CLI
3. creates a symmetric link with `trackstate ticket link --type "relates to"`
4. runs the exact ticket step `trackstate ticket show --key TS-2`
5. verifies the JSON response contains a `links` array entry with canonical
   inward metadata for Issue A:
   `{"type":"relates to","target":"TS-1","direction":"inward"}`

## Install dependencies

No Python packages are required beyond the standard library and the repository's
existing test dependencies.

The test requires:
- a Flutter SDK available on `PATH`, because the repository-local compiled CLI
  harness runs through `flutter test`
- the `git` CLI available on `PATH`

## Run this test

```bash
python -m unittest testing.tests.TS-657.test_ts_657
```

## Environment variables

No ticket-specific environment variables are required.

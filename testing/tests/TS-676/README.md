# TS-676

Verifies that `trackstate read ticket --key TS-2` maps an inward asymmetric
relationship to the correct user-visible label in the canonical top-level
`links` array.

The automation:
1. seeds a disposable Local Git TrackState repository with one existing issue
2. creates Issue A (`TS-1`) and Issue B (`TS-2`) through the real CLI
3. creates an asymmetric link with `trackstate ticket link --type "blocks"`
4. runs the exact ticket step `trackstate read ticket --key TS-2`
5. verifies the JSON response contains a `links` array entry with the specific
   inward metadata for Issue A:
   `{"type":"is blocked by","target":"TS-1","direction":"inward"}`

## Install dependencies

No Python packages are required beyond the standard library and the repository's
existing test dependencies.

The test requires:
- a Flutter SDK available on `PATH`, because the repository-local compiled CLI
  harness runs through `flutter test`
- the `git` CLI available on `PATH`

## Run this test

```bash
python -m unittest testing.tests.TS-676.test_ts_676
```

## Environment variables

No ticket-specific environment variables are required.

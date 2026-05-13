# TS-662

Validates that the local CLI can link two distinct issues with `relates to`
and persists the relationship metadata on the source issue.

The automation:
1. seeds a disposable Local Git TrackState repository with one existing issue
2. creates Issue A (`TS-1`) and Issue B (`TS-2`) through the real CLI
3. runs `trackstate ticket link --key TS-1 --target-key TS-2 --type "relates to"`
4. verifies the visible JSON success response reports the outward relationship
5. checks `TS/TS-1/links.json` stores the canonical persisted relation to `TS-2`

## Install dependencies

No Python packages are required beyond the standard library and the repository's
existing test dependencies.

The test requires:
- a Flutter SDK available on `PATH`, because the repository-local compiled CLI
  harness runs through `flutter test`
- the `git` CLI available on `PATH`

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-662 -p 'test_*.py' -v
```

## Environment variables

No ticket-specific environment variables are required.

# TS-273

Verifies that the live TrackState CLI maps an unsupported hosted provider to
the documented machine-readable error contract, including exit code `5`,
`ok: false`, and the `UNSUPPORTED_PROVIDER` / `unsupported` error fields.

## Run this test

```bash
python3 -m unittest discover -s testing/tests/TS-273 -p 'test_*.py' -v
```

## Required configuration

No Python packages are required beyond the standard library. The repository
under test must have a Dart SDK available on `PATH`, or `TRACKSTATE_DART_BIN`
must point to the Dart executable used to run `dart run trackstate`.

## Expected passing output

```text
test_live_cli_maps_unsupported_provider_to_documented_error_contract (test_ts_273.UnsupportedProviderCliContractTest.test_live_cli_maps_unsupported_provider_to_documented_error_contract) ... ok

----------------------------------------------------------------------
Ran 1 test in <time>

OK
```

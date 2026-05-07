# TS-38

This test verifies the repository abstraction boundary through a Dart probe that:

1. Instantiates `ProviderBackedTrackStateRepository` with a fake `TrackStateProviderAdapter`.
2. Connects the repository through its public API.
3. Reads the repository's `ProviderSession` contract from the repository instance.
4. Verifies the neutral session fields and capability flags through that contract.

The Python test remains the entrypoint for CI, but it delegates the product-facing assertion to the Dart probe via `testing/core/interfaces/provider_contract_probe.py`.

## Install dependencies

1. Ensure a Dart SDK is already available on `PATH`, or set `TS38_DART_BIN=/absolute/path/to/dart`.
2. From `testing/tests/TS-38/dart_probe/`, run `dart --disable-analytics pub get --offline` (the probe uses only local path dependencies).

## Run

```bash
python -m unittest discover -s testing/tests/TS-38 -p 'test_*.py'
```

## Environment variables

- `TS38_DART_BIN` (optional): absolute path to a preinstalled `dart` executable when it is not on `PATH`.

## Expected passing output

```text
.
----------------------------------------------------------------------
Ran 1 test in <time>

OK
```

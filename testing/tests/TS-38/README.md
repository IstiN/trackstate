# TS-38

This test verifies the repository abstraction boundary through a Dart probe that:

1. Instantiates `ProviderBackedTrackStateRepository` with a fake `TrackStateProviderAdapter`.
2. Connects the repository through its public API.
3. Reads the repository's `ProviderSession` contract from the repository instance.
4. Verifies the neutral session fields and capability flags through that contract.

The Python test remains the entrypoint for CI, but it delegates the product-facing assertion to the Dart probe via `testing/core/interfaces/provider_contract_probe.py`. Test-layer wiring lives in `testing/tests/support/provider_contract_probe_factory.py`, which composes the framework runtime with `testing/components/services/provider_contract_inspector.py` without making the component instantiate framework code directly.

## Install dependencies

1. Optional: point `TS38_DART_BIN=/absolute/path/to/dart` at a preinstalled Dart SDK to skip bootstrapping.
2. Otherwise the shared Python runtime in `testing/frameworks/python/dart_probe_runtime.py` bootstraps the pinned SDK declared in `testing/core/config/dart_sdk_runtime.json` into `~/.cache/trackstate-test-tools` (override with `TS38_TOOL_CACHE` or `TRACKSTATE_TOOL_CACHE`).
3. The probe still runs `dart --disable-analytics pub get --offline`; it uses only local path dependencies.

## Run

```bash
python -m unittest discover -s testing/tests/TS-38 -p 'test_*.py'
```

## Environment variables

- `TS38_DART_BIN` (optional): absolute path to a preinstalled `dart` executable when it is not on `PATH`.
- `TRACKSTATE_DART_BIN` (optional): shared fallback path to a preinstalled `dart` executable.
- `TS38_TOOL_CACHE` / `TRACKSTATE_TOOL_CACHE` (optional): directory used for the bootstrapped Dart SDK cache.

## Expected passing output

```text
.
----------------------------------------------------------------------
Ran 1 test in <time>

OK
```

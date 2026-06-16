# TS-87

This test verifies that a previously obtained
`ProviderBackedTrackStateRepository.session` reference remains reactive after the
provider state changes:

1. Instantiate the repository with a mutable fake `TrackStateProviderAdapter`.
2. Start `connect()` and capture the public `session` reference while the
   provider is still in the connecting state.
3. Update the fake provider to a connected/write-capable state and let
   authentication finish.
4. Inspect the previously captured `session` reference without re-reading
   `repository.session`.

The Python test is the CI entrypoint, but it delegates the product-facing
assertions to a Dart probe so the live repository contract is exercised through
the same public API the app uses.

## Install dependencies

1. Optional: point `TS38_DART_BIN=/absolute/path/to/dart` at a preinstalled
   Dart SDK to skip bootstrapping.
2. Otherwise the shared Python runtime in
   `testing/frameworks/python/dart_probe_runtime.py` bootstraps the pinned SDK
   declared in `testing/core/config/dart_sdk_runtime.json` into
   `~/.cache/trackstate-test-tools` (override with `TS38_TOOL_CACHE` or
   `TRACKSTATE_TOOL_CACHE`).
3. The probe runs `dart --disable-analytics pub get --offline`; it uses only
   local path dependencies.

## Run

```bash
python -m unittest discover -s testing/tests/TS-87 -p 'test_*.py' -v
```

## Environment variables

- `TS38_DART_BIN` (optional): absolute path to a preinstalled `dart`
  executable when it is not on `PATH`.
- `TRACKSTATE_DART_BIN` (optional): shared fallback path to a preinstalled
  `dart` executable.
- `TS38_TOOL_CACHE` / `TRACKSTATE_TOOL_CACHE` (optional): directory used for
  the bootstrapped Dart SDK cache.

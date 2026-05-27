# TS-89

This test verifies the successful provider connection lifecycle through the live
`ProviderBackedTrackStateRepository` contract:

1. Instantiate the repository with a fake `TrackStateProviderAdapter` that
   authenticates successfully and exposes full permissions.
2. Call the repository's public `connect()` API and await completion.
3. Read the public `session` getter from the repository instance.
4. Verify that the exposed `ProviderSession` is non-null, reports
   `ProviderConnectionState.connected`, and keeps all capability flags enabled.

The Python test remains the CI entrypoint, while the Dart probe exercises the
production repository implementation through the same public boundary that app
code depends on.

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
python3 -m unittest discover -s testing/tests/TS-89 -p 'test_*.py' -v
```

## Environment variables

- `TS38_DART_BIN` (optional): absolute path to a preinstalled `dart`
  executable when it is not on `PATH`.
- `TRACKSTATE_DART_BIN` (optional): shared fallback path to a preinstalled
  `dart` executable.
- `TS38_TOOL_CACHE` / `TRACKSTATE_TOOL_CACHE` (optional): directory used for
  the bootstrapped Dart SDK cache.
- `TS89_RESULT_PATH` (optional): file path where the test writes the raw probe
  observation payload for reporting.

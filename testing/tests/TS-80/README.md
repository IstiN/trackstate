# TS-80

This test verifies the repository session contract when the provider rejects a
connection attempt. The Dart probe:

1. Instantiates `ProviderBackedTrackStateRepository` with a fake
   `TrackStateProviderAdapter` whose `authenticate()` method always fails with an
   unauthorized error.
2. Attempts to connect through the repository's public API.
3. Reads the public `session` getter after the failed connection attempt.
4. Verifies that the observable session contract reports a disconnected/error
   state and that write/management capability flags remain false.

The Python test remains the CI entrypoint, while the Dart probe exercises the
live product implementation through the same public repository boundary used by
the app.

## Install dependencies

1. Optional: point `TS38_DART_BIN=/absolute/path/to/dart` at a preinstalled
   Dart SDK to skip bootstrapping.
2. Otherwise the shared Python runtime in
   `testing/frameworks/python/dart_probe_runtime.py` bootstraps the pinned SDK
   declared in `testing/core/config/dart_sdk_runtime.json` into
   `~/.cache/trackstate-test-tools` (override with `TS38_TOOL_CACHE` or
   `TRACKSTATE_TOOL_CACHE`).
3. The probe still runs `dart --disable-analytics pub get --offline`; it uses
   only local path dependencies.

## Run

```bash
python3 -m unittest discover -s testing/tests/TS-80 -p 'test_*.py'
```

## Environment variables

- `TS38_DART_BIN` (optional): absolute path to a preinstalled `dart` executable
  when it is not on `PATH`.
- `TRACKSTATE_DART_BIN` (optional): shared fallback path to a preinstalled
  `dart` executable.
- `TS38_TOOL_CACHE` / `TRACKSTATE_TOOL_CACHE` (optional): directory used for
  the bootstrapped Dart SDK cache.

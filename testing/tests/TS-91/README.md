# TS-91

This test verifies the repository session contract immediately after
`ProviderBackedTrackStateRepository` instantiation:

1. Instantiate the repository with a fake `TrackStateProviderAdapter`.
2. Read the public `session` getter without calling `connect()`.
3. Verify that the observable session contract is non-null, reports a safe
   pre-connection state, and keeps every capability flag restricted by default.

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
python3 -m unittest discover -s testing/tests/TS-91 -p 'test_*.py'
```

## Environment variables

- `TS38_DART_BIN` (optional): absolute path to a preinstalled `dart` executable
  when it is not on `PATH`.
- `TRACKSTATE_DART_BIN` (optional): shared fallback path to a preinstalled
  `dart` executable.
- `TS38_TOOL_CACHE` / `TRACKSTATE_TOOL_CACHE` (optional): directory used for
  the bootstrapped Dart SDK cache.

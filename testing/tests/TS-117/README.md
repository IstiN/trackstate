# TS-117

This test verifies that `ProviderBackedTrackStateRepository.session` exposes the
public restricted failure contract when the GitHub connection attempt fails with
HTTP 403 and HTTP 500 responses:

1. Instantiate `ProviderBackedTrackStateRepository` with the live
   `GitHubTrackStateProvider`.
2. Configure the provider's HTTP client to return either `403 Forbidden` or
   `500 Internal Server Error` for the initial repository connection request.
3. Call `connect()` through the repository's public API and then read the
   public `session` getter.
4. Verify that the observable session contract reports
   `ProviderConnectionState.error` and that all restricted capability flags are
   `false` for both failure codes.

The Python test remains the CI entrypoint, while the Dart probe exercises the
live product implementation through the same repository and provider classes the
application uses.

## Install dependencies

1. Optional: point `TS38_DART_BIN=/absolute/path/to/dart` at a preinstalled
   Dart SDK to skip bootstrapping.
2. Otherwise the shared Python runtime in
   `testing/frameworks/python/dart_probe_runtime.py` bootstraps the pinned SDK
   declared in `testing/core/config/dart_sdk_runtime.json` into
   `~/.cache/trackstate-test-tools` (override with `TS38_TOOL_CACHE` or
   `TRACKSTATE_TOOL_CACHE`).
3. The probe runs `dart --disable-analytics pub get --offline`; it uses only
   local path dependencies, including a probe-local `package:flutter` stub for
   `foundation.dart`.

## Run

```bash
python -m unittest discover -s testing/tests/TS-117 -p 'test_*.py' -v
```

## Environment variables

- `TS38_DART_BIN` (optional): absolute path to a preinstalled `dart`
  executable when it is not on `PATH`.
- `TRACKSTATE_DART_BIN` (optional): shared fallback path to a preinstalled
  `dart` executable.
- `TS38_TOOL_CACHE` / `TRACKSTATE_TOOL_CACHE` (optional): directory used for
  the bootstrapped Dart SDK cache.

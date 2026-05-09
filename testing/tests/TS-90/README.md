# TS-90

This test verifies that `ProviderBackedTrackStateRepository.session` recovers
from a failed connection attempt after a successful retry:

1. Instantiate the repository with a retryable fake
   `TrackStateProviderAdapter`.
2. Call `connect()` once while the provider is configured to fail with an
   unauthorized error and capture the public failure-state session.
3. Reconfigure the same provider to allow authentication and expose
   write-capable permissions.
4. Call `connect()` again and require a fresh public `repository.session`
   observation to expose `ProviderConnectionState.connected` with the updated
   capabilities.

The Python test remains the CI entrypoint, but it delegates the product-facing
assertion to a Dart probe through
`testing/core/interfaces/provider_session_sync_probe.py`. Wiring stays in
`testing/tests/support/provider_session_retry_probe_factory.py`, and the
component layer keeps the framework runtime out of the test body.

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
python -m unittest discover -s testing/tests/TS-90 -p 'test_*.py' -v
```

## Environment variables

- `TS38_DART_BIN` (optional): absolute path to a preinstalled `dart`
  executable when it is not on `PATH`.
- `TRACKSTATE_DART_BIN` (optional): shared fallback path to a preinstalled
  `dart` executable.
- `TS38_TOOL_CACHE` / `TRACKSTATE_TOOL_CACHE` (optional): directory used for
  the bootstrapped Dart SDK cache.

# TS-88

This test verifies that `ProviderBackedTrackStateRepository.session` exposes the
public lifecycle transition from `disconnected` to `connecting`:

1. Instantiate the repository with a mutable fake `TrackStateProviderAdapter`.
2. Read `repository.session` immediately after initialization and require a
   public `ProviderConnectionState.disconnected` observation.
3. Start `connect()` while the fake provider remains blocked in authentication.
4. Read `repository.session` while authentication is in progress and require a
   public `ProviderConnectionState.connecting` observation.

The Python test is the CI entrypoint, but it delegates the product-facing
assertion to a Dart probe through
`testing/core/interfaces/provider_session_sync_probe.py`. Wiring stays in
`testing/tests/support/provider_session_lifecycle_probe_factory.py`, and the
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
python -m unittest discover -s testing/tests/TS-88 -p 'test_*.py' -v
```

## Environment variables

- `TS38_DART_BIN` (optional): absolute path to a preinstalled `dart`
  executable when it is not on `PATH`.
- `TRACKSTATE_DART_BIN` (optional): shared fallback path to a preinstalled
  `dart` executable.
- `TS38_TOOL_CACHE` / `TRACKSTATE_TOOL_CACHE` (optional): directory used for
  the bootstrapped Dart SDK cache.

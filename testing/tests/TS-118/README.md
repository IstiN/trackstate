# TS-118

This test verifies that `ProviderBackedTrackStateRepository.connect()` leaves the
public `repository.session` contract in `ProviderConnectionState.error` when an
unexpected operation-level exception interrupts the connection flow:

1. Instantiate `ProviderBackedTrackStateRepository` with a fake
   `TrackStateProviderAdapter`.
2. Allow authentication to succeed once, but throw a generic runtime error from
   the post-auth permission sync that still happens inside `connect()`.
3. Catch the surfaced exception through the repository's public API.
4. Read the public `session` getter and require `connectionState=error` with
   restricted capabilities instead of a disconnected fallback.

The Python test remains the CI entrypoint, but it delegates the product-facing
assertion to a Dart probe through
`testing/core/interfaces/provider_session_sync_probe.py`. Wiring stays in
`testing/tests/support/provider_unexpected_operation_exception_probe_factory.py`,
and the component layer keeps the framework runtime out of the test body.

## Install dependencies

1. Optional: point `TS38_DART_BIN=/absolute/path/to/dart` at a preinstalled
   Dart SDK to skip bootstrapping.
2. Otherwise the shared Python runtime in
   `testing/frameworks/python/dart_probe_runtime.py` bootstraps the pinned SDK
   declared in `testing/core/config/dart_sdk_runtime.json` into
   `~/.cache/trackstate-test-tools` (override with `TS38_TOOL_CACHE` or
   `TRACKSTATE_TOOL_CACHE`).
3. The probe runs `dart --disable-analytics pub get --offline`; it uses only
   local path dependencies, including a minimal local `flutter` stub so the
   repository's public session model can be compiled in a plain Dart runtime.

## Run

```bash
python -m unittest discover -s testing/tests/TS-118 -p 'test_*.py' -v
```

## Environment variables

- `TS38_DART_BIN` (optional): absolute path to a preinstalled `dart`
  executable when it is not on `PATH`.
- `TRACKSTATE_DART_BIN` (optional): shared fallback path to a preinstalled
  `dart` executable.
- `TS38_TOOL_CACHE` / `TRACKSTATE_TOOL_CACHE` (optional): directory used for
  the bootstrapped Dart SDK cache.

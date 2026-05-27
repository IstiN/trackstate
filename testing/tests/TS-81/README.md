# TS-81

This test verifies that `ProviderBackedTrackStateRepository.session` reflects a
live provider transition during an in-flight connection:

1. Instantiate the repository with a mutable fake `TrackStateProviderAdapter`.
2. Start `connect()` while the fake provider remains blocked in an initial
   connecting state.
3. Read `repository.session` before authentication completes and require a
   public `ProviderConnectionState.connecting` observation with
   `canCreateBranch == false`.
4. Update the fake provider to a connected/write-capable state, finish
   authentication, and require the same public session getter to expose
   `ProviderConnectionState.connected` with `canCreateBranch == true`.

The Python test is the CI entrypoint, but it delegates the product-facing
assertion to a Dart probe through
`testing/core/interfaces/provider_session_sync_probe.py`. Wiring stays in
`testing/tests/support/provider_session_sync_probe_factory.py`, and the
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
python -m unittest discover -s testing/tests/TS-81 -p 'test_*.py' -v
```

## Environment variables

- `TS38_DART_BIN` (optional): absolute path to a preinstalled `dart`
  executable when it is not on `PATH`.
- `TRACKSTATE_DART_BIN` (optional): shared fallback path to a preinstalled
  `dart` executable.
- `TS38_TOOL_CACHE` / `TRACKSTATE_TOOL_CACHE` (optional): directory used for
  the bootstrapped Dart SDK cache.

## Expected passing output

```text
test_repository_session_reflects_live_provider_updates ... ok
```

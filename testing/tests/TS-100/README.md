# TS-100

This test verifies that one previously obtained
`ProviderBackedTrackStateRepository.session` reference remains reactive across
multiple consecutive lifecycle transitions:

1. Start `connect()` with a mutable fake `TrackStateProviderAdapter` and capture
   the public `session` reference while the repository is still connecting.
2. Transition the provider to a connected, write-capable state with
   `resolvedUserIdentity == reactive-user` and confirm the same captured session
   object updates automatically.
3. Trigger a failed reconnect that drives the public contract back to the
   restricted `ProviderConnectionState.error` state and confirm the same
   captured session object updates again.
4. Recover with another successful reconnect using
   `resolvedUserIdentity == updated-user` and `canCreateBranch == false`,
   verifying the original session reference still reflects the latest state.

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
python -m unittest discover -s testing/tests/TS-100 -p 'test_*.py' -v
```

## Environment variables

- `TS38_DART_BIN` (optional): absolute path to a preinstalled `dart`
  executable when it is not on `PATH`.
- `TRACKSTATE_DART_BIN` (optional): shared fallback path to a preinstalled
  `dart` executable.
- `TS38_TOOL_CACHE` / `TRACKSTATE_TOOL_CACHE` (optional): directory used for
  the bootstrapped Dart SDK cache.

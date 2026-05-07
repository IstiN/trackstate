# TS-39

Validates that TrackState startup stays on the hosted GitHub runtime by default, that an explicit runtime define is required to switch to Local Git, and that the hosted repository access UI is shown for the startup-selected repository.

## Install dependencies

Run `flutter pub get` from the repository root.

## Run this test

Run `flutter test testing/tests/TS-39/ts39_runtime_resolution_test.dart`.

## Environment and configuration

No extra secrets are required. The test uses `testing/tests/TS-39/config.yaml`, a hosted-runtime fixture client, and the app's default startup configuration. The Local Git override probe additionally runs `testing/tests/TS-39/support/ts39_runtime_define_override_probe_test.dart` with `--dart-define=TRACKSTATE_RUNTIME=local-git` on IO platforms.

## Expected passing output

The main test command reports `2 passed, 0 failed`, and the override probe confirms that the define-based startup path resolves `LocalTrackStateRepository` on IO platforms.

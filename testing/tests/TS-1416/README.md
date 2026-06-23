# TS-1416

Regression test for TS-1408. Verifies that the hosted runtime onboarding UI renders the GitHub repository access elements during startup on the Web platform.

## Install dependencies

Run `flutter pub get` from the repository root.

## Run this test

Run `flutter test testing/tests/TS-1416/ts1416_hosted_runtime_onboarding_test.dart`.

## Environment and configuration

No extra secrets are required. The test uses `testing/tests/TS-1416/config.yaml` and the shared hosted-runtime fixture client from `testing/fixtures/hosted_runtime_client_fixture.dart`.

## Expected passing output

The test command reports `1 passed, 0 failed` and confirms that `Connect GitHub`, `Fine-grained token`, and `Remember on this browser` are visible after startup.

# TS-1417

Regression test for TS-1408. Verifies that the hosted runtime onboarding widget hierarchy is stable for automated probes: the `Connect GitHub` elements are found deterministically, their count remains unchanged across consecutive pump cycles, and the dialog descendants (`Fine-grained token`, helper text, and `Remember on this browser`) remain unique and stable.

## Install dependencies

Run `flutter pub get` from the repository root.

## Run this test

Run `flutter test testing/tests/TS-1417/ts1417_onboarding_ui_probe_stability_test.dart`.

## Environment and configuration

No extra secrets are required. The test uses `testing/tests/TS-1417/config.yaml` and the shared hosted-runtime fixture client from `testing/fixtures/hosted_runtime_client_fixture.dart`.

## Expected passing output

The test command reports `1 passed, 0 failed` and confirms that the automated probe observes a stable widget hierarchy with a consistent, non-zero count of `Connect GitHub` elements and exactly one of each dialog descendant element.

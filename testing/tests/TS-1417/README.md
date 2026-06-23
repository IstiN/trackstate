# TS-1417

Regression test for TS-1408. Verifies that the hosted runtime onboarding widget hierarchy is stable for automated probes: the `Connect GitHub` element is found deterministically, remains visible across consecutive pump cycles, and does not produce duplicate or flickering widgets.

## Install dependencies

Run `flutter pub get` from the repository root.

## Run this test

Run `flutter test testing/tests/TS-1417/ts1417_onboarding_ui_probe_stability_test.dart`.

## Environment and configuration

No extra secrets are required. The test uses `testing/tests/TS-1417/config.yaml` and reuses the hosted-runtime fixture client from `testing/tests/TS-39/support/`.

## Expected passing output

The test command reports `1 passed, 0 failed` and confirms that the automated probe observes a stable widget hierarchy with exactly one `Connect GitHub` element.

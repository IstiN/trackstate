from __future__ import annotations

from pathlib import Path
import unittest

from testing.core.interfaces.provider_session_reference_reactivity_probe import (
    ProviderSessionReferenceReactivityProbe,
)
from testing.tests.support.provider_session_multi_transition_probe_factory import (
    create_provider_session_multi_transition_probe,
)


class ProviderSessionMultiTransitionReactivityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.probe: ProviderSessionReferenceReactivityProbe = (
            create_provider_session_multi_transition_probe(self.repository_root)
        )

    def test_single_session_reference_updates_across_multiple_state_transitions(
        self,
    ) -> None:
        result = self.probe.inspect()
        failures = self._build_failures(result)

        self.assertEqual(
            failures,
            [],
            "TS-100 multi-transition session reactivity regression:\n- "
            + "\n- ".join(failures),
        )

    def _build_failures(self, result) -> list[str]:
        failures: list[str] = []
        if not result.succeeded:
            failures.append(
                "The Dart probe could not be analyzed before the multi-transition "
                "session contract was verified.\n"
                f"{result.analyze_output}"
            )
            return failures

        observation = result.observation_payload or {}
        if observation.get("status") != "passed":
            details = [str(observation.get("error") or "The Dart probe reported a failure.")]
            stack_trace = observation.get("stackTrace") or observation.get("stack_trace")
            if stack_trace:
                details.append(str(stack_trace))
            failures.append("\n".join(details))
            return failures

        initial_reference = observation.get("initialSessionReference")
        first_connected_reference = observation.get("firstConnectedSessionReference")
        first_connected_latest = observation.get("firstConnectedRepositorySession")
        disconnected_reference = observation.get("disconnectedSessionReference")
        disconnected_latest = observation.get("disconnectedRepositorySession")
        final_connected_reference = observation.get("finalConnectedSessionReference")
        final_connected_latest = observation.get("finalConnectedRepositorySession")

        self.assertIsInstance(initial_reference, dict)
        self.assertIsInstance(first_connected_reference, dict)
        self.assertIsInstance(first_connected_latest, dict)
        self.assertIsInstance(disconnected_reference, dict)
        self.assertIsInstance(disconnected_latest, dict)
        self.assertIsInstance(final_connected_reference, dict)
        self.assertIsInstance(final_connected_latest, dict)

        initial_payload = initial_reference or {}
        first_connected_payload = first_connected_reference or {}
        first_connected_latest_payload = first_connected_latest or {}
        disconnected_payload = disconnected_reference or {}
        disconnected_latest_payload = disconnected_latest or {}
        final_connected_payload = final_connected_reference or {}
        final_connected_latest_payload = final_connected_latest or {}

        if initial_payload.get("connectionState") != "ProviderConnectionState.connecting":
            failures.append(
                "Step 2 failed: the captured session reference did not expose the "
                "expected connecting state while the first authentication was in progress. "
                f"Observed initial reference: {initial_payload}"
            )
        if initial_payload.get("canCreateBranch") is not False:
            failures.append(
                "Step 2 failed: the captured session reference exposed branch creation "
                "before the provider completed the first successful connection. "
                f"Observed initial reference: {initial_payload}"
            )

        if first_connected_latest_payload.get("connectionState") != "ProviderConnectionState.connected":
            failures.append(
                "Step 4 failed: a fresh repository.session getter did not expose the "
                "expected connected state after the first provider transition. "
                f"Observed latest session: {first_connected_latest_payload}"
            )
        if first_connected_payload.get("connectionState") != "ProviderConnectionState.connected":
            failures.append(
                "Step 4 failed: the previously obtained session reference did not update "
                "to connected after the first provider transition. "
                f"Observed session reference: {first_connected_payload}\n"
                f"Observed fresh repository.session: {first_connected_latest_payload}"
            )
        if first_connected_payload.get("resolvedUserIdentity") != "reactive-user":
            failures.append(
                "Step 4 failed: the previously obtained session reference did not expose "
                "the first connected identity. "
                f"Observed session reference: {first_connected_payload}"
            )
        if first_connected_payload.get("canCreateBranch") is not True:
            failures.append(
                "Step 4 failed: the previously obtained session reference did not expose "
                "canCreateBranch=true after the first successful connection. "
                f"Observed session reference: {first_connected_payload}"
            )
        if observation.get("sameInstanceAfterFirstConnection") is not True:
            failures.append(
                "Step 4 failed: the updated first connected session was no longer the "
                "same instance returned by repository.session."
            )

        if disconnected_latest_payload.get("connectionState") != "ProviderConnectionState.disconnected":
            failures.append(
                "Step 6 failed: a fresh repository.session getter did not expose the "
                "expected disconnected state after the failed reconnect. "
                f"Observed latest session: {disconnected_latest_payload}"
            )
        if disconnected_payload.get("connectionState") != "ProviderConnectionState.disconnected":
            failures.append(
                "Step 6 failed: the previously obtained session reference did not update "
                "to the restricted disconnected state after the failed reconnect. "
                f"Observed session reference: {disconnected_payload}\n"
                f"Observed fresh repository.session: {disconnected_latest_payload}"
            )
        for field in (
            "canRead",
            "canWrite",
            "canCreateBranch",
            "canManageAttachments",
            "canCheckCollaborators",
        ):
            if disconnected_payload.get(field) is not False:
                failures.append(
                    "Step 6 failed: the previously obtained session reference did not "
                    f"clear restricted capability '{field}' after the failed reconnect. "
                    f"Observed session reference: {disconnected_payload}"
                )
        if observation.get("sameInstanceAfterDisconnect") is not True:
            failures.append(
                "Step 6 failed: the disconnected session was no longer the same instance "
                "returned by repository.session."
            )

        if final_connected_latest_payload.get("connectionState") != "ProviderConnectionState.connected":
            failures.append(
                "Step 8 failed: a fresh repository.session getter did not expose the "
                "expected recovered connected state after the final reconnect. "
                f"Observed latest session: {final_connected_latest_payload}"
            )
        if final_connected_payload.get("connectionState") != "ProviderConnectionState.connected":
            failures.append(
                "Step 8 failed: the previously obtained session reference did not recover "
                "to connected after the final provider transition. "
                f"Observed session reference: {final_connected_payload}\n"
                f"Observed fresh repository.session: {final_connected_latest_payload}"
            )
        if final_connected_payload.get("resolvedUserIdentity") != "updated-user":
            failures.append(
                "Step 8 failed: the previously obtained session reference did not expose "
                "the updated recovered identity. "
                f"Observed session reference: {final_connected_payload}"
            )
        if final_connected_payload.get("canCreateBranch") is not False:
            failures.append(
                "Step 8 failed: the previously obtained session reference did not expose "
                "the updated canCreateBranch=false restriction after recovery. "
                f"Observed session reference: {final_connected_payload}"
            )
        if observation.get("sameInstanceAfterRecovery") is not True:
            failures.append(
                "Step 8 failed: the recovered session was no longer the same instance "
                "returned by repository.session."
            )

        return failures


if __name__ == "__main__":
    unittest.main()

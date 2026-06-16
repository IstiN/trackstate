from __future__ import annotations

from pathlib import Path
import unittest

from testing.core.interfaces.provider_session_sync_probe import (
    ProviderSessionSyncProbe,
)
from testing.tests.support.provider_session_lifecycle_probe_factory import (
    create_provider_session_lifecycle_probe,
)


class ProviderSessionLifecyclePropagationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.probe: ProviderSessionSyncProbe = create_provider_session_lifecycle_probe(
            self.repository_root
        )

    def test_repository_session_reflects_disconnected_to_connecting_transition(
        self,
    ) -> None:
        result = self.probe.inspect()
        failures = self._build_failures(result)

        self.assertEqual(
            failures,
            [],
            "TS-88 lifecycle propagation regression:\n- " + "\n- ".join(failures),
        )

    def _build_failures(self, result) -> list[str]:
        failures: list[str] = []
        if not result.succeeded:
            failures.append(
                "The Dart probe could not be analyzed before the public session "
                "lifecycle was verified.\n"
                f"{result.analyze_output}"
            )
            return failures

        observation = result.observation_payload or {}
        if observation.get("status") != "passed":
            error_message = observation.get("error") or "The Dart probe reported a failure."
            stack_trace = observation.get("stackTrace") or observation.get("stack_trace")
            details = [str(error_message)]
            if stack_trace:
                details.append(str(stack_trace))
            failures.append("\n".join(details))
            return failures

        initial_session = observation.get("initialSession")
        connecting_session = observation.get("connectingSession")

        self.assertIsInstance(initial_session, dict)
        self.assertIsInstance(connecting_session, dict)

        initial_payload = initial_session or {}
        connecting_payload = connecting_session or {}

        if initial_payload.get("connectionState") != "ProviderConnectionState.disconnected":
            failures.append(
                "Step 2 failed: the repository session did not expose the required "
                "disconnected state immediately after initialization. "
                f"Observed initial session: {initial_payload}"
            )
        if connecting_payload.get("connectionState") != "ProviderConnectionState.connecting":
            failures.append(
                "Step 4 failed: the repository session did not expose the required "
                "connecting state after authentication started. "
                f"Observed connecting session: {connecting_payload}"
            )
        return failures


if __name__ == "__main__":
    unittest.main()

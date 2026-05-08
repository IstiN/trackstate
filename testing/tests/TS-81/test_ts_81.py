from __future__ import annotations

from pathlib import Path
import unittest

from testing.core.interfaces.provider_session_sync_probe import (
    ProviderSessionSyncProbe,
)
from testing.tests.support.provider_session_sync_probe_factory import (
    create_provider_session_sync_probe,
)


class ProviderSessionSynchronizationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.probe: ProviderSessionSyncProbe = create_provider_session_sync_probe(
            self.repository_root
        )

    def test_repository_session_reflects_live_provider_updates(self) -> None:
        result = self.probe.inspect()
        failures = self._build_failures(result)

        self.assertEqual(
            failures,
            [],
            "TS-81 session state synchronization regression:\n- "
            + "\n- ".join(failures),
        )

    def _build_failures(self, result) -> list[str]:
        failures: list[str] = []
        if not result.succeeded:
            analyze_output = result.analyze_output
            if (
                "The getter 'connecting' isn't defined for the type "
                "'ProviderConnectionState'" in analyze_output
                or "There's no constant named 'connecting' in "
                "'ProviderConnectionState'" in analyze_output
            ):
                failures.append(
                    "Step 2 failed: the public ProviderConnectionState contract "
                    "cannot represent a connecting repository session, so product "
                    "logic cannot observe the required in-progress state.\n"
                    f"{analyze_output}"
                )
            if not failures:
                failures.append(
                    "The Dart probe could not be analyzed before the public session "
                    "contract was verified.\n"
                    f"{analyze_output}"
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
        final_session = observation.get("finalSession")

        self.assertIsInstance(initial_session, dict)
        self.assertIsInstance(final_session, dict)

        initial_payload = initial_session or {}
        final_payload = final_session or {}

        if initial_payload.get("connectionState") != "ProviderConnectionState.connecting":
            failures.append(
                "Step 2 failed: the repository session did not expose the required "
                f"connecting state. Observed initial session: {initial_payload}"
            )
        if initial_payload.get("canCreateBranch") is not False:
            failures.append(
                "Step 2 failed: canCreateBranch should stay disabled until the "
                f"provider reports its connected/write-capable state. Observed initial session: {initial_payload}"
            )
        if final_payload.get("connectionState") != "ProviderConnectionState.connected":
            failures.append(
                "Step 4 failed: the repository session did not update to connected "
                f"after the provider transition. Observed final session: {final_payload}"
            )
        if final_payload.get("canCreateBranch") is not True:
            failures.append(
                "Step 4 failed: the repository session did not reflect the updated "
                f"canCreateBranch capability after the provider transition. Observed final session: {final_payload}"
            )
        return failures


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from pathlib import Path
import unittest

from testing.core.interfaces.provider_session_reference_reactivity_probe import (
    ProviderSessionReferenceReactivityProbe,
)
from testing.tests.support.provider_session_reference_reactivity_probe_factory import (
    create_provider_session_reference_reactivity_probe,
)


class ProviderSessionReferenceReactivityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.probe: ProviderSessionReferenceReactivityProbe = (
            create_provider_session_reference_reactivity_probe(self.repository_root)
        )

    def test_previously_obtained_session_reference_updates_without_reaccessing_getter(
        self,
    ) -> None:
        result = self.probe.inspect()
        failures = self._build_failures(result)

        self.assertEqual(
            failures,
            [],
            "TS-87 session reference reactivity regression:\n- "
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
                    "still cannot expose a connecting repository session, so the "
                    "reactive reference cannot be observed during connection.\n"
                    f"{analyze_output}"
                )
            if not failures:
                failures.append(
                    "The Dart probe could not be analyzed before the live session "
                    "reference contract was verified.\n"
                    f"{analyze_output}"
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
        updated_reference = observation.get("updatedSessionReference")
        latest_session = observation.get("latestRepositorySession")

        self.assertIsInstance(initial_reference, dict)
        self.assertIsInstance(updated_reference, dict)
        self.assertIsInstance(latest_session, dict)

        initial_payload = initial_reference or {}
        updated_payload = updated_reference or {}
        latest_payload = latest_session or {}

        if initial_payload.get("connectionState") != "ProviderConnectionState.connecting":
            failures.append(
                "Step 2 failed: the captured session reference did not expose the "
                f"expected connecting state. Observed initial reference: {initial_payload}"
            )
        if initial_payload.get("canCreateBranch") is not False:
            failures.append(
                "Step 2 failed: the captured session reference should remain "
                "read-only before authentication completes. "
                f"Observed initial reference: {initial_payload}"
            )

        if latest_payload.get("connectionState") != "ProviderConnectionState.connected":
            failures.append(
                "Step 3 failed: after the provider updated, a fresh "
                "`repository.session` getter still did not report `connected`. "
                f"Observed latest session: {latest_payload}"
            )
        if latest_payload.get("canCreateBranch") is not True:
            failures.append(
                "Step 3 failed: after the provider enabled branch creation, a fresh "
                "`repository.session` getter still did not reflect that capability. "
                f"Observed latest session: {latest_payload}"
            )

        if updated_payload.get("connectionState") != "ProviderConnectionState.connected":
            failures.append(
                "Step 4 failed: the previously obtained session reference did not "
                "update its `connectionState` automatically after the provider "
                "transition.\n"
                f"Observed updated reference: {updated_payload}\n"
                f"Observed fresh repository.session: {latest_payload}"
            )
        if updated_payload.get("canCreateBranch") is not True:
            failures.append(
                "Step 4 failed: the previously obtained session reference did not "
                "update `canCreateBranch` automatically after the provider changed "
                "permissions.\n"
                f"Observed updated reference: {updated_payload}\n"
                f"Observed fresh repository.session: {latest_payload}"
            )

        return failures


if __name__ == "__main__":
    unittest.main()

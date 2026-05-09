from __future__ import annotations

from pathlib import Path
import unittest

from testing.core.interfaces.provider_session_reference_reactivity_probe import (
    ProviderSessionReferenceReactivityProbe,
)
from testing.tests.support.provider_session_reference_reactivity_probe_factory import (
    create_provider_session_reference_reactivity_probe,
)


class ProviderSessionProbeRuntimeCompatibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.probe: ProviderSessionReferenceReactivityProbe = (
            create_provider_session_reference_reactivity_probe(self.repository_root)
        )

    def test_probe_runs_and_reports_live_session_updates(self) -> None:
        result = self.probe.inspect()

        self.assertTrue(
            result.succeeded,
            "The TS-87 Dart probe failed before it could verify the live session "
            f"contract.\nAnalyze output:\n{result.analyze_output}\nRun output:\n{result.run_output}",
        )

        observation = result.observation_payload or {}
        self.assertEqual(
            observation.get("status"),
            "passed",
            f"Expected the TS-87 Dart probe to pass, got: {observation}",
        )
        self.assertTrue(
            observation.get("sameInstanceAsLatestGetter"),
            f"Expected the captured session reference to stay identical to the latest getter, got: {observation}",
        )

        updated_reference = observation.get("updatedSessionReference") or {}
        self.assertEqual(
            updated_reference.get("connectionState"),
            "ProviderConnectionState.connected",
            f"Expected the captured session reference to become connected, got: {observation}",
        )
        self.assertTrue(
            updated_reference.get("canCreateBranch"),
            f"Expected the captured session reference to reflect write capability, got: {observation}",
        )


if __name__ == "__main__":
    unittest.main()

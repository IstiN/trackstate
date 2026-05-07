from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.provider_contract_inspector import create_provider_contract_probe
from testing.core.interfaces.provider_contract_probe import ProviderContractProbe


class ProviderAbstractionBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.inspector: ProviderContractProbe = create_provider_contract_probe(self.repository_root)

    def test_repository_depends_on_neutral_session_and_capability_flags(self) -> None:
        result = self.inspector.inspect()
        failures = self._build_failures(result)

        self.assertEqual(failures, [], "TS-38 provider abstraction boundary regression:\n- " + "\n- ".join(failures))

    def _build_failures(self, result) -> list[str]:
        failures: list[str] = []
        if not result.succeeded:
            analyze_output = result.analyze_output
            if "Undefined class 'ProviderSession'" in analyze_output:
                failures.append(
                    "Step 3 failed: no public ProviderSession type is available from the repository boundary."
                )
            if "The getter 'session' isn't defined for the type 'ProviderBackedTrackStateRepository'" in analyze_output:
                failures.append(
                    "Step 2 failed: ProviderBackedTrackStateRepository does not expose a public ProviderSession/session contract for product logic."
                )

            missing_session_fields = [
                field
                for field in ("providerType", "connectionState", "resolvedUserIdentity")
                if f"The getter '{field}' isn't defined for the type 'ProviderSession'" in analyze_output
            ]
            if missing_session_fields:
                failures.append(
                    "Step 3 failed: ProviderSession is missing required neutral fields "
                    f"{missing_session_fields}."
                )

            missing_capability_flags = [
                field
                for field in (
                    "canRead",
                    "canWrite",
                    "canCreateBranch",
                    "canManageAttachments",
                    "canCheckCollaborators",
                )
                if f"The getter '{field}' isn't defined for the type 'ProviderSession'" in analyze_output
            ]
            if missing_capability_flags:
                failures.append(
                    "Step 4 failed: neutral capability flags are incomplete. Missing "
                    f"{missing_capability_flags} on ProviderSession."
                )

            if not failures:
                failures.append(
                    "Probe failed before the repository boundary could be verified.\n"
                    + analyze_output
                )
            return failures

        session = result.session_payload or {}
        for field in ("providerType", "connectionState", "resolvedUserIdentity"):
            if field not in session:
                failures.append(f"Step 3 failed: ProviderSession did not expose '{field}'.")
        for field in (
            "canRead",
            "canWrite",
            "canCreateBranch",
            "canManageAttachments",
            "canCheckCollaborators",
        ):
            if field not in session:
                failures.append(
                    f"Step 4 failed: neutral capability flag '{field}' is missing from ProviderSession."
                )
        return failures


if __name__ == "__main__":
    unittest.main()

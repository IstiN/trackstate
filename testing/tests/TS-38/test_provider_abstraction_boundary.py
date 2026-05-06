from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.provider_contract_inspector import ProviderContractInspector


class ProviderAbstractionBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.inspector = ProviderContractInspector(self.repository_root)

    def test_repository_depends_on_neutral_session_and_capability_flags(self) -> None:
        observation = self.inspector.inspect()
        expected_session_fields = {
            "providerType",
            "connectionState",
            "resolvedUserIdentity",
        }
        expected_capability_flags = {
            "canRead",
            "canWrite",
            "canCreateBranch",
            "canManageAttachments",
            "canCheckCollaborators",
        }

        failures: list[str] = []

        if not observation.repository_exposes_session:
            failures.append(
                "Step 2 failed: ProviderBackedTrackStateRepository does not expose a public "
                "ProviderSession/session contract for product logic."
            )

        missing_session_fields = sorted(
            expected_session_fields.difference(observation.provider_session_fields)
        )
        if observation.provider_session_file is None:
            failures.append(
                "Step 3 failed: no ProviderSession class was found anywhere under lib/."
            )
        elif missing_session_fields:
            failures.append(
                "Step 3 failed: ProviderSession is missing required neutral fields "
                f"{missing_session_fields}. Observed fields: "
                f"{list(observation.provider_session_fields)} in {observation.provider_session_file}."
            )

        missing_capability_flags = sorted(
            expected_capability_flags.difference(observation.capability_flags)
        )
        if missing_capability_flags:
            failures.append(
                "Step 4 failed: neutral capability flags are incomplete. Missing "
                f"{missing_capability_flags}. Observed flags: {list(observation.capability_flags)}"
                + (
                    f" in {observation.capability_contract_file}."
                    if observation.capability_contract_file
                    else " across lib/."
                )
            )

        if observation.repository_specific_types:
            failures.append(
                "Expected a provider-neutral boundary, but repository code still references "
                f"provider-specific types {list(observation.repository_specific_types)}."
            )

        self.assertEqual(
            failures,
            [],
            "TS-38 provider abstraction boundary regression:\n- "
            + "\n- ".join(failures),
        )


if __name__ == "__main__":
    unittest.main()

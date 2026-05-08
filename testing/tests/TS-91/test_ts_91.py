from __future__ import annotations

from pathlib import Path
import unittest

from testing.core.interfaces.provider_contract_probe import ProviderContractProbe
from testing.tests.support.provider_default_session_probe_factory import (
    create_provider_default_session_probe,
)


class ProviderDefaultSessionContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.probe: ProviderContractProbe = create_provider_default_session_probe(
            self.repository_root
        )

    def test_repository_instantiation_exposes_a_non_null_restricted_session(self) -> None:
        result = self.probe.inspect()
        failures = self._build_failures(result)

        self.assertEqual(
            failures,
            [],
            "TS-91 default session contract regression:\n- " + "\n- ".join(failures),
        )

    def _build_failures(self, result) -> list[str]:
        failures: list[str] = []
        if not result.succeeded:
            failures.append(
                "Probe failed before the repository default-session contract could be verified.\n"
                + result.analyze_output
            )
            return failures

        payload = result.session_payload or {}
        session = payload.get("session")
        if session is None:
            failures.append(
                "Step 2 failed: repository.session was null immediately after repository "
                "instantiation, before connect() was ever called.\n"
                "Expected a visible restricted ProviderSession so product logic can inspect "
                "connectionState and capability flags by default.\n"
                f"Observed probe payload: {payload}"
            )
            return failures

        if not isinstance(session, dict):
            failures.append(
                "Step 2 failed: repository.session did not serialize into an inspectable "
                f"contract payload.\nObserved value: {session!r}"
            )
            return failures

        connection_state = session.get("connectionState")
        if connection_state not in (
            "ProviderConnectionState.disconnected",
            "ProviderConnectionState.uninitialized",
        ):
            failures.append(
                "Step 3 failed: the default repository session did not expose a safe "
                "pre-connection state.\nExpected connectionState to be disconnected "
                "or uninitialized immediately after instantiation.\n"
                f"Observed connectionState: {connection_state!r}\n"
                f"Observed session: {session}"
            )

        for field in (
            "canRead",
            "canWrite",
            "canCreateBranch",
            "canManageAttachments",
            "canCheckCollaborators",
        ):
            if session.get(field) is not False:
                failures.append(
                    f"Step 3 failed: capability flag '{field}' was "
                    f"{session.get(field)!r} instead of false before connect().\n"
                    f"Observed session: {session}"
                )

        return failures


if __name__ == "__main__":
    unittest.main()

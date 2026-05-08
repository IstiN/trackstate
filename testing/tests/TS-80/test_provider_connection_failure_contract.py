from __future__ import annotations

from pathlib import Path
import unittest

from testing.core.interfaces.provider_contract_probe import ProviderContractProbe
from testing.tests.support.provider_connection_failure_probe_factory import (
    create_provider_connection_failure_probe,
)


class ProviderConnectionFailureContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.inspector: ProviderContractProbe = (
            create_provider_connection_failure_probe(self.repository_root)
        )

    def test_session_contract_reflects_failed_connection_and_restricts_access(self) -> None:
        result = self.inspector.inspect()
        failures = self._build_failures(result)

        self.assertEqual(
            failures,
            [],
            "TS-80 session failure contract regression:\n- " + "\n- ".join(failures),
        )

    def _build_failures(self, result) -> list[str]:
        failures: list[str] = []
        if not result.succeeded:
            failures.append(
                "Probe failed before the repository failure-state contract could be verified.\n"
                + result.analyze_output
            )
            return failures

        payload = result.session_payload or {}
        authenticate_attempts = payload.get("authenticateAttempts")
        if authenticate_attempts != 1:
            failures.append(
                "Step 1 failed: the failure-configured provider was not exercised exactly once.\n"
                f"Observed authenticateAttempts: {authenticate_attempts!r}\n"
                f"Observed probe payload: {payload}"
            )

        session = payload.get("session")
        connect_error = payload.get("connectError")
        if session is None:
            failures.append(
                "Step 2 failed: repository.session remained null after the failed "
                "connection attempt, so product logic cannot observe a restricted "
                "provider session contract.\n"
                f"Observed connect error: {connect_error!r}\n"
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
            "ProviderConnectionState.error",
        ):
            failures.append(
                "Step 3 failed: the session contract did not reflect a failed connection.\n"
                "Expected connectionState to be disconnected/error after the provider "
                "rejected authentication.\n"
                f"Observed connectionState: {connection_state!r}\n"
                f"Observed connect error: {connect_error!r}"
            )

        for field in (
            "canWrite",
            "canCreateBranch",
            "canManageAttachments",
            "canCheckCollaborators",
        ):
            if session.get(field) is not False:
                failures.append(
                    f"Step 4 failed: capability flag '{field}' was "
                    f"{session.get(field)!r} instead of false after the failed "
                    "connection attempt.\n"
                    f"Observed session: {session}"
                )

        return failures


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from testing.core.interfaces.provider_contract_probe import ProviderContractProbe
from testing.tests.support.provider_successful_connection_probe_factory import (
    create_provider_successful_connection_probe,
)


class ProviderSuccessfulConnectionContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.probe: ProviderContractProbe = create_provider_successful_connection_probe(
            self.repository_root
        )

    def test_repository_session_reflects_connected_authorized_state(self) -> None:
        result = self.probe.inspect()
        self._write_result_if_requested(result.session_payload or {})
        failures = self._build_failures(result)

        self.assertEqual(
            failures,
            [],
            "TS-89 successful connection contract regression:\n- "
            + "\n- ".join(failures),
        )

    def _build_failures(self, result) -> list[str]:
        failures: list[str] = []
        if not result.succeeded:
            failures.append(
                "Probe failed before the repository success-state contract could be verified.\n"
                + result.analyze_output
            )
            return failures

        payload = result.session_payload or {}
        authenticate_attempts = payload.get("authenticateAttempts")
        if authenticate_attempts != 1:
            failures.append(
                "Step 1 failed: the success-configured provider was not exercised "
                "exactly once.\n"
                f"Observed authenticateAttempts: {authenticate_attempts!r}\n"
                f"Observed probe payload: {payload}"
            )

        connected_user = payload.get("connectedUser")
        if connected_user != "connected-user":
            failures.append(
                "Step 2 failed: connect() did not return the expected authenticated "
                "user identity from the provider.\n"
                f"Observed connectedUser: {connected_user!r}\n"
                f"Observed probe payload: {payload}"
            )

        session = payload.get("session")
        if session is None:
            failures.append(
                "Step 3 failed: repository.session was null after a successful "
                "connection.\n"
                f"Observed probe payload: {payload}"
            )
            return failures

        if not isinstance(session, dict):
            failures.append(
                "Step 3 failed: repository.session did not serialize into an "
                f"inspectable contract payload.\nObserved value: {session!r}"
            )
            return failures

        if session.get("connectionState") != "ProviderConnectionState.connected":
            failures.append(
                "Step 4 failed: the session contract did not reflect an active "
                "connected state after successful authentication.\n"
                f"Observed connectionState: {session.get('connectionState')!r}\n"
                f"Observed session: {session}"
            )

        if session.get("resolvedUserIdentity") != "connected-user":
            failures.append(
                "Step 4 failed: the session contract did not expose the authenticated "
                "user identity after connection.\n"
                f"Observed resolvedUserIdentity: {session.get('resolvedUserIdentity')!r}\n"
                f"Observed session: {session}"
            )

        for field in (
            "canWrite",
            "canCreateBranch",
            "canManageAttachments",
            "canCheckCollaborators",
        ):
            if session.get(field) is not True:
                failures.append(
                    f"Step 5 failed: capability flag '{field}' was "
                    f"{session.get(field)!r} instead of true after successful "
                    "authentication.\n"
                    f"Observed session: {session}"
                )

        return failures

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS89_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()

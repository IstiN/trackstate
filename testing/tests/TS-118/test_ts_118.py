from __future__ import annotations

from pathlib import Path
import unittest

from testing.core.interfaces.provider_session_sync_probe import (
    ProviderSessionSyncProbe,
)
from testing.tests.support.provider_unexpected_operation_exception_probe_factory import (
    create_provider_unexpected_operation_exception_probe,
)


class ProviderSessionUnexpectedOperationExceptionTest(unittest.TestCase):
    EXPECTED_ERROR_MARKER = "Unexpected operation-level exception for TS-118."

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.probe: ProviderSessionSyncProbe = (
            create_provider_unexpected_operation_exception_probe(self.repository_root)
        )

    def test_connect_runtime_exception_keeps_public_session_in_error_state(self) -> None:
        result = self.probe.inspect()
        failures = self._build_failures(result)

        self.assertEqual(
            failures,
            [],
            "TS-118 unexpected operation exception regression:\n- "
            + "\n- ".join(failures),
        )

    def _build_failures(self, result) -> list[str]:
        failures: list[str] = []
        if not result.succeeded:
            failures.append(
                "The Dart probe could not be analyzed before the unexpected "
                "operation-level connection failure contract was verified.\n"
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

        session = observation.get("session")
        self.assertIsInstance(session, dict)
        session_payload = session or {}

        connect_error = observation.get("connectError")
        if not connect_error:
            failures.append(
                "Step 3 failed: connect() did not surface the configured runtime "
                "exception back to the caller.\n"
                f"Observed payload: {observation}"
            )
        elif self.EXPECTED_ERROR_MARKER not in str(connect_error):
            failures.append(
                "Step 3 failed: connect() surfaced an unexpected error payload.\n"
                f"Expected error marker: {self.EXPECTED_ERROR_MARKER!r}\n"
                f"Observed connectError: {connect_error!r}"
            )

        if observation.get("authenticateAttempts") != 1:
            failures.append(
                "Step 2 failed: the provider authenticate() call was not exercised "
                "exactly once.\n"
                f"Observed authenticateAttempts: {observation.get('authenticateAttempts')!r}\n"
                f"Observed payload: {observation}"
            )

        if observation.get("permissionRequests") != 2:
            failures.append(
                "Step 2 failed: the provider did not reach the post-auth "
                "permission sync that throws the unexpected runtime exception.\n"
                f"Observed permissionRequests: {observation.get('permissionRequests')!r}\n"
                f"Observed payload: {observation}"
            )

        if session_payload.get("connectionState") != "ProviderConnectionState.error":
            failures.append(
                "Step 4 failed: repository.session did not expose the required "
                "error state after the unexpected operation-level exception.\n"
                "Expected connectionState to remain error instead of falling back "
                "to disconnected.\n"
                f"Observed session: {session_payload}\n"
                f"Observed connectError: {connect_error!r}"
            )

        for field in (
            "canRead",
            "canWrite",
            "canCreateBranch",
            "canManageAttachments",
            "canCheckCollaborators",
        ):
            if session_payload.get(field) is not False:
                failures.append(
                    f"Step 4 failed: failure-state field '{field}' was "
                    f"{session_payload.get(field)!r} instead of false.\n"
                    f"Observed session: {session_payload}"
                )

        return failures


if __name__ == "__main__":
    unittest.main()

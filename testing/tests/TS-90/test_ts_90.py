from __future__ import annotations

from pathlib import Path
import unittest

from testing.core.interfaces.provider_session_sync_probe import (
    ProviderSessionSyncProbe,
)
from testing.tests.support.provider_session_retry_probe_factory import (
    create_provider_session_retry_probe,
)


class ProviderSessionRetryRecoveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.probe: ProviderSessionSyncProbe = create_provider_session_retry_probe(
            self.repository_root
        )

    def test_repository_session_recovers_from_failed_connection_after_retry(self) -> None:
        result = self.probe.inspect()
        failures = self._build_failures(result)

        self.assertEqual(
            failures,
            [],
            "TS-90 retry recovery regression:\n- " + "\n- ".join(failures),
        )

    def _build_failures(self, result) -> list[str]:
        failures: list[str] = []
        if not result.succeeded:
            failures.append(
                "The Dart probe could not be analyzed before the failed-to-connected "
                "session retry contract was verified.\n"
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

        failed_session = observation.get("failedSession")
        recovered_session = observation.get("recoveredSession")

        self.assertIsInstance(failed_session, dict)
        self.assertIsInstance(recovered_session, dict)

        failed_payload = failed_session or {}
        recovered_payload = recovered_session or {}

        first_connect_error = observation.get("firstConnectError")
        if not first_connect_error:
            failures.append(
                "Step 1 failed: the initial connection attempt did not surface the "
                "expected authentication failure.\n"
                f"Observed payload: {observation}"
            )
        authenticate_attempts_after_failure = observation.get(
            "authenticateAttemptsAfterFailure"
        )
        if authenticate_attempts_after_failure != 1:
            failures.append(
                "Step 1 failed: the failure-configured provider was not exercised "
                "exactly once before the retry.\n"
                f"Observed authenticateAttemptsAfterFailure: {authenticate_attempts_after_failure!r}\n"
                f"Observed payload: {observation}"
            )

        failed_connection_state = failed_payload.get("connectionState")
        if failed_connection_state not in (
            "ProviderConnectionState.disconnected",
            "ProviderConnectionState.error",
        ):
            failures.append(
                "Step 2 failed: the session getter did not expose a restricted "
                "failure-state contract after the unauthorized connection.\n"
                f"Observed failed session: {failed_payload}\n"
                f"Observed firstConnectError: {first_connect_error!r}"
            )

        for field in (
            "canRead",
            "canWrite",
            "canCreateBranch",
            "canManageAttachments",
            "canCheckCollaborators",
        ):
            if failed_payload.get(field) is not False:
                failures.append(
                    f"Step 2 failed: failure-state field '{field}' was "
                    f"{failed_payload.get(field)!r} instead of false.\n"
                    f"Observed failed session: {failed_payload}"
                )

        authenticate_attempts_after_retry = observation.get(
            "authenticateAttemptsAfterRetry"
        )
        if authenticate_attempts_after_retry != 2:
            failures.append(
                "Step 4 failed: the provider was not exercised a second time for the "
                "successful retry.\n"
                f"Observed authenticateAttemptsAfterRetry: {authenticate_attempts_after_retry!r}\n"
                f"Observed payload: {observation}"
            )

        if observation.get("connectedUserLogin") != "retry-user":
            failures.append(
                "Step 4 failed: the successful retry did not return the expected "
                "authenticated user identity.\n"
                f"Observed connectedUserLogin: {observation.get('connectedUserLogin')!r}"
            )

        if recovered_payload.get("connectionState") != "ProviderConnectionState.connected":
            failures.append(
                "Step 5 failed: the session getter did not update to the expected "
                "connected state after the retry.\n"
                f"Observed recovered session: {recovered_payload}"
            )

        if recovered_payload.get("resolvedUserIdentity") != "retry-user":
            failures.append(
                "Step 5 failed: the recovered session did not expose the successful "
                "authenticated user identity.\n"
                f"Observed recovered session: {recovered_payload}"
            )

        for field in (
            "canRead",
            "canWrite",
            "canCreateBranch",
            "canManageAttachments",
            "canCheckCollaborators",
        ):
            if recovered_payload.get(field) is not True:
                failures.append(
                    f"Step 5 failed: recovered field '{field}' was "
                    f"{recovered_payload.get(field)!r} instead of true after the "
                    "successful retry.\n"
                    f"Observed recovered session: {recovered_payload}"
                )

        return failures


if __name__ == "__main__":
    unittest.main()

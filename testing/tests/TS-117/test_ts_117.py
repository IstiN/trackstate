from __future__ import annotations

from pathlib import Path
import unittest

from testing.core.interfaces.provider_session_sync_probe import (
    ProviderSessionSyncProbe,
)
from testing.tests.support.provider_http_failure_state_probe_factory import (
    create_provider_http_failure_state_probe,
)


class ProviderHttpFailureStateTest(unittest.TestCase):
    EXPECTED_REPOSITORY_IDENTITY = "mock/error-repository"
    EXPECTED_REQUEST_URL = "https://api.github.com/repos/mock/error-repository"
    EXPECTED_FAILURES = {
        403: 'GitHub connection failed (403): {"message":"Forbidden"}',
        500: 'GitHub connection failed (500): {"message":"Internal Server Error"}',
    }

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.probe: ProviderSessionSyncProbe = (
            create_provider_http_failure_state_probe(self.repository_root)
        )

    def test_repository_session_maps_403_and_500_failures_to_error_state(self) -> None:
        result = self.probe.inspect()
        failures = self._build_failures(result)

        self.assertEqual(
            failures,
            [],
            "TS-117 HTTP failure-state regression:\n- " + "\n- ".join(failures),
        )

    def _build_failures(self, result) -> list[str]:
        failures: list[str] = []
        if not result.succeeded:
            failures.append(
                "The Dart probe could not be analyzed before the HTTP failure-state "
                "contract was verified.\n"
                f"{result.analyze_output}"
            )
            return failures

        payload = result.observation_payload or {}
        if payload.get("status") != "passed":
            details = [str(payload.get("error") or "The Dart probe reported a failure.")]
            stack_trace = payload.get("stackTrace") or payload.get("stack_trace")
            if stack_trace:
                details.append(str(stack_trace))
            failures.append("\n".join(details))
            return failures

        scenarios = payload.get("scenarios")
        if not isinstance(scenarios, list):
            failures.append(
                "The probe did not return the expected scenario list for the 403/500 "
                f"connection failures.\nObserved payload: {payload}"
            )
            return failures

        scenarios_by_code = {
            scenario.get("statusCode"): scenario
            for scenario in scenarios
            if isinstance(scenario, dict)
        }

        for status_code, expected_error in self.EXPECTED_FAILURES.items():
            scenario = scenarios_by_code.get(status_code)
            if not isinstance(scenario, dict):
                failures.append(
                    "The probe did not return an inspectable scenario payload for the "
                    f"HTTP {status_code} failure.\nObserved scenarios: {scenarios}"
                )
                continue

            if scenario.get("status") != "passed":
                failures.append(
                    f"Step 2 failed for HTTP {status_code}: the connection attempt did "
                    "not surface a handled failure scenario.\n"
                    f"Observed scenario: {scenario}"
                )
                continue

            connect_error = scenario.get("connectError")
            if connect_error != expected_error:
                failures.append(
                    f"Step 2 failed for HTTP {status_code}: connect() did not surface "
                    "the expected provider error.\n"
                    f"Expected connectError: {expected_error!r}\n"
                    f"Observed scenario: {scenario}"
                )

            if scenario.get("getCalls") != 1:
                failures.append(
                    f"Step 2 failed for HTTP {status_code}: the GitHub connection "
                    "request was not exercised exactly once.\n"
                    f"Observed getCalls: {scenario.get('getCalls')!r}\n"
                    f"Observed scenario: {scenario}"
                )

            if scenario.get("requestedUrls") != [self.EXPECTED_REQUEST_URL]:
                failures.append(
                    f"Step 2 failed for HTTP {status_code}: the provider did not hit "
                    "the expected GitHub repository endpoint.\n"
                    f"Expected requestedUrls: {[self.EXPECTED_REQUEST_URL]!r}\n"
                    f"Observed requestedUrls: {scenario.get('requestedUrls')!r}"
                )

            session = scenario.get("session")
            if not isinstance(session, dict):
                failures.append(
                    f"Step 3 failed for HTTP {status_code}: repository.session was not "
                    "returned as an inspectable public contract.\n"
                    f"Observed session: {session!r}"
                )
                continue

            if session.get("connectionState") != "ProviderConnectionState.error":
                failures.append(
                    f"Step 3 failed for HTTP {status_code}: repository.session did not "
                    "expose ProviderConnectionState.error after the failed connection.\n"
                    f"Observed session: {session}"
                )

            if session.get("resolvedUserIdentity") != self.EXPECTED_REPOSITORY_IDENTITY:
                failures.append(
                    f"Step 3 failed for HTTP {status_code}: repository.session did not "
                    "retain the repository identity for the restricted failure state.\n"
                    f"Expected resolvedUserIdentity: {self.EXPECTED_REPOSITORY_IDENTITY!r}\n"
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
                        f"Step 4 failed for HTTP {status_code}: capability flag "
                        f"'{field}' was {session.get(field)!r} instead of false.\n"
                        f"Observed session: {session}"
                    )

        return failures


if __name__ == "__main__":
    unittest.main()

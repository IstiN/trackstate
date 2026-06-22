from __future__ import annotations

import time
import unittest
from unittest import mock

from testing.components.services.github_pages_workflow_probe import (
    GitHubCliError,
    GitHubPagesWorkflowProbe,
)
from testing.core.models.github_pages_workflow_probe_config import (
    GitHubPagesWorkflowProbeConfig,
)


class _UnusedGitHubApiClient:
    def request_text(self, **_: object) -> str:
        raise AssertionError(
            "Workflow registration tests should not hit the gh client."
        )


class _UnusedUrlTextReader:
    def read_text(self, **_: object) -> str:
        raise AssertionError(
            "Workflow registration tests should not fetch live URLs."
        )


class _WorkflowRegistrationProbe(GitHubPagesWorkflowProbe):
    def __init__(self) -> None:
        super().__init__(
            GitHubPagesWorkflowProbeConfig(
                upstream_repository="IstiN/trackstate-setup",
                workflow_file="install-update-trackstate.yml",
                workflow_ref="main",
                trackstate_ref="main",
            ),
            github_api_client=_UnusedGitHubApiClient(),
            url_text_reader=_UnusedUrlTextReader(),
            fork_registration_timeout_seconds=2,
            workflow_registration_timeout_seconds=2,
            poll_interval_seconds=0,
        )
        self._actions_enabled = False

    def _authenticated_login(self) -> str:
        return "ai-teammate"

    def _repository_exists(self, repository: str) -> bool:
        del repository
        return True

    def _create_fork(self) -> None:
        raise AssertionError(
            "Workflow registration tests should not create a fork."
        )

    def _wait_for_repository(self, repository: str) -> bool:
        del repository
        return True

    def _enable_actions(self, repository: str) -> None:
        del repository
        self._actions_enabled = True

    def _gh_json(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        field_args: list[str] | None = None,
        stdin_json: dict[str, object] | None = None,
    ) -> dict[str, object]:
        del method, field_args, stdin_json
        if endpoint == "repos/ai-teammate/trackstate-setup/actions/workflows":
            if self._actions_enabled:
                return {
                    "workflows": [
                        {
                            "path": ".github/workflows/install-update-trackstate.yml",
                        }
                    ]
                }
            return {"workflows": []}
        raise AssertionError(f"Unexpected gh api endpoint: {endpoint}")


class _UnregisteredWorkflowProbe(_WorkflowRegistrationProbe):
    def _gh_json(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        field_args: list[str] | None = None,
        stdin_json: dict[str, object] | None = None,
    ) -> dict[str, object]:
        del method, field_args, stdin_json
        if endpoint == "repos/ai-teammate/trackstate-setup/actions/workflows":
            # Even with Actions enabled, GitHub never registers the workflow.
            return {"workflows": []}
        raise AssertionError(f"Unexpected gh api endpoint: {endpoint}")


class _MockClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += max(seconds, 0.0)


class _SlowWorkflowRegistrationProbe(GitHubPagesWorkflowProbe):
    """Simulates a fork where GitHub registers the workflow only after a delay."""

    def __init__(self, workflow_registration_timeout_seconds: int) -> None:
        super().__init__(
            GitHubPagesWorkflowProbeConfig(
                upstream_repository="IstiN/trackstate-setup",
                workflow_file="install-update-trackstate.yml",
                workflow_ref="main",
                trackstate_ref="main",
            ),
            github_api_client=_UnusedGitHubApiClient(),
            url_text_reader=_UnusedUrlTextReader(),
            workflow_registration_timeout_seconds=workflow_registration_timeout_seconds,
            poll_interval_seconds=10,
        )

    def _authenticated_login(self) -> str:
        return "ai-teammate"

    def _repository_exists(self, repository: str) -> bool:
        del repository
        return True

    def _create_fork(self) -> None:
        raise AssertionError(
            "Slow registration tests should not create a fork."
        )

    def _wait_for_repository(self, repository: str) -> bool:
        del repository
        return True

    def _enable_actions(self, repository: str) -> None:
        del repository

    def _gh_json(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        field_args: list[str] | None = None,
        stdin_json: dict[str, object] | None = None,
    ) -> dict[str, object]:
        del method, field_args, stdin_json
        if endpoint == "repos/ai-teammate/trackstate-setup/actions/workflows":
            # Register after 350 simulated seconds, which is past the original
            # 300-second timeout but within the extended 600-second window.
            if time.time() >= 1350.0:
                return {
                    "workflows": [
                        {
                            "path": ".github/workflows/install-update-trackstate.yml",
                        }
                    ]
                }
            return {"workflows": []}
        raise AssertionError(f"Unexpected gh api endpoint: {endpoint}")


class GitHubPagesWorkflowProbeRegistrationTest(unittest.TestCase):
    def test_enables_actions_before_polling_for_workflow_registration(self) -> None:
        probe = _WorkflowRegistrationProbe()

        selected_repository = probe._select_repository_for_execution()

        self.assertEqual(selected_repository, "ai-teammate/trackstate-setup")
        self.assertTrue(
            probe._actions_enabled,
            "The probe must enable GitHub Actions on the fork before it can "
            "rely on workflow registration.",
        )

    def test_times_out_when_workflow_stays_unregistered(self) -> None:
        probe = _UnregisteredWorkflowProbe()

        with self.assertRaisesRegex(
            GitHubCliError,
            "GitHub did not register install-update-trackstate.yml",
        ):
            probe._select_repository_for_execution()

    def test_workflow_registration_uses_extended_timeout(self) -> None:
        """Regression test for TS-1398.

        GitHub can take more than the original 300-second window to register a
        workflow in a freshly forked repository. The probe must wait long enough
        for registration to complete instead of timing out and failing the test.
        """
        clock = _MockClock()
        probe = _SlowWorkflowRegistrationProbe(
            workflow_registration_timeout_seconds=600,
        )

        with mock.patch("time.time", clock.time), mock.patch(
            "time.sleep", clock.sleep
        ):
            selected_repository = probe._select_repository_for_execution()

        self.assertEqual(selected_repository, "ai-teammate/trackstate-setup")
        self.assertGreaterEqual(
            clock.now,
            1000.0 + 350.0,
            "The probe should have polled until the workflow registered."
        )
        self.assertLess(
            clock.now,
            1000.0 + 600.0,
            "The probe should not have hit the extended timeout."
        )


if __name__ == "__main__":
    unittest.main()

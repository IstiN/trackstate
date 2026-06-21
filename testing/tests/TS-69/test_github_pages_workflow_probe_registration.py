from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()

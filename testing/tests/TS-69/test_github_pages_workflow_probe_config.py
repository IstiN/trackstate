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
        raise AssertionError("Repository selection tests should not hit the gh client.")


class _UnusedUrlTextReader:
    def read_text(self, **_: object) -> str:
        raise AssertionError(
            "Repository selection tests should not fetch live page content."
        )


class _RepositorySelectionProbe(GitHubPagesWorkflowProbe):
    def __init__(
        self,
        *,
        config: GitHubPagesWorkflowProbeConfig,
        authenticated_login: str,
        repository_exists: bool,
        workflow_registered: bool = True,
        repository_available: bool = True,
    ) -> None:
        super().__init__(
            config,
            github_api_client=_UnusedGitHubApiClient(),
            url_text_reader=_UnusedUrlTextReader(),
            poll_interval_seconds=0,
        )
        self._authenticated_login_value = authenticated_login
        self._repository_exists_value = repository_exists
        self._workflow_registered_value = workflow_registered
        self._repository_available_value = repository_available
        self.create_fork_calls = 0

    def _authenticated_login(self) -> str:
        return self._authenticated_login_value

    def _repository_exists(self, repository: str) -> bool:
        return self._repository_exists_value

    def _create_fork(self) -> None:
        self.create_fork_calls += 1

    def _wait_for_repository(self, repository: str) -> bool:
        return self._repository_available_value

    def _wait_for_workflow_registration(self, repository: str) -> bool:
        return self._workflow_registered_value


class GitHubPagesWorkflowProbeConfigTest(unittest.TestCase):
    def test_rejects_upstream_owner_login(self) -> None:
        probe = _RepositorySelectionProbe(
            config=GitHubPagesWorkflowProbeConfig(
                upstream_repository="IstiN/trackstate-setup",
                workflow_file="install-update-trackstate.yml",
                workflow_ref="main",
                trackstate_ref="main",
            ),
            authenticated_login="IstiN",
            repository_exists=True,
        )

        with self.assertRaisesRegex(
            GitHubCliError,
            "authenticated login IstiN owns the upstream repository",
        ):
            probe._select_repository_for_execution()

    def test_creates_missing_fork_for_authenticated_login_namespace(self) -> None:
        probe = _RepositorySelectionProbe(
            config=GitHubPagesWorkflowProbeConfig(
                upstream_repository="IstiN/trackstate-setup",
                workflow_file="install-update-trackstate.yml",
                workflow_ref="main",
                trackstate_ref="main",
            ),
            authenticated_login="ai-teammate",
            repository_exists=False,
        )

        self.assertEqual(
            probe._select_repository_for_execution(),
            "ai-teammate/trackstate-setup",
        )
        self.assertEqual(probe.create_fork_calls, 1)

    def test_uses_authenticated_login_fork_when_it_is_registered(self) -> None:
        probe = _RepositorySelectionProbe(
            config=GitHubPagesWorkflowProbeConfig(
                upstream_repository="IstiN/trackstate-setup",
                workflow_file="install-update-trackstate.yml",
                workflow_ref="main",
                trackstate_ref="main",
            ),
            authenticated_login="ai-teammate",
            repository_exists=True,
        )

        self.assertEqual(
            probe._select_repository_for_execution(),
            "ai-teammate/trackstate-setup",
        )


if __name__ == "__main__":
    unittest.main()

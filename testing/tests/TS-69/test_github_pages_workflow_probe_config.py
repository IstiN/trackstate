from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.github_pages_workflow_probe import (
    GitHubCliError,
    GitHubPagesWorkflowProbe,
)
from testing.core.models.github_pages_workflow_probe_config import (
    GitHubPagesWorkflowProbeConfig,
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
        super().__init__(Path.cwd(), config, poll_interval_seconds=0)
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
    def test_rejects_upstream_repository_as_requested_repository(self) -> None:
        probe = _RepositorySelectionProbe(
            config=GitHubPagesWorkflowProbeConfig(
                upstream_repository="IstiN/trackstate-setup",
                requested_repository="IstiN/trackstate-setup",
                workflow_file="install-update-trackstate.yml",
                workflow_ref="main",
                trackstate_ref="main",
            ),
            authenticated_login="IstiN",
            repository_exists=True,
        )

        with self.assertRaisesRegex(
            GitHubCliError,
            "requires validating a forked repository",
        ):
            probe._select_repository_for_execution()

    def test_rejects_missing_fork_when_authenticated_login_cannot_create_it(self) -> None:
        probe = _RepositorySelectionProbe(
            config=GitHubPagesWorkflowProbeConfig(
                upstream_repository="IstiN/trackstate-setup",
                requested_repository="ai-teammate/trackstate-setup",
                workflow_file="install-update-trackstate.yml",
                workflow_ref="main",
                trackstate_ref="main",
            ),
            authenticated_login="IstiN",
            repository_exists=False,
        )

        with self.assertRaisesRegex(
            GitHubCliError,
            "cannot create a fork in that owner namespace",
        ):
            probe._select_repository_for_execution()

        self.assertEqual(probe.create_fork_calls, 0)

    def test_uses_configured_fork_repository_when_it_is_registered(self) -> None:
        probe = _RepositorySelectionProbe(
            config=GitHubPagesWorkflowProbeConfig(
                upstream_repository="IstiN/trackstate-setup",
                requested_repository="ai-teammate/trackstate-setup",
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

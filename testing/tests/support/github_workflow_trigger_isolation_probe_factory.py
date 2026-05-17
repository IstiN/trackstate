from __future__ import annotations

from pathlib import Path

from testing.components.services.github_workflow_trigger_isolation_probe import (
    GitHubWorkflowTriggerIsolationProbeService,
)
from testing.core.config.github_workflow_trigger_isolation_config import (
    GitHubWorkflowTriggerIsolationConfig,
)
from testing.core.interfaces.github_workflow_trigger_isolation_probe import (
    GitHubWorkflowTriggerIsolationProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient
from testing.frameworks.python.gh_cli_workflow_run_log_reader import (
    GhCliWorkflowRunLogReader,
)
from testing.tests.support.github_repository_file_page_factory import (
    create_github_repository_file_page,
)


def create_github_workflow_trigger_isolation_probe(
    repository_root: Path,
    *,
    screenshot_directory: Path | None = None,
) -> GitHubWorkflowTriggerIsolationProbe:
    config = GitHubWorkflowTriggerIsolationConfig.from_file(
        repository_root / "testing/tests/TS-709/config.yaml"
    )
    return GitHubWorkflowTriggerIsolationProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
        workflow_run_log_reader=GhCliWorkflowRunLogReader(repository_root),
        file_page_factory=create_github_repository_file_page,
        screenshot_directory=screenshot_directory,
    )

from __future__ import annotations

from pathlib import Path

from testing.components.services.github_accessibility_log_validation_step_presence_probe import (
    GitHubAccessibilityLogValidationStepPresenceProbeService,
)
from testing.core.config.github_accessibility_pull_request_gate_config import (
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateProbe,
)
from testing.core.interfaces.github_workflow_run_log_reader import (
    GitHubWorkflowRunLogReader,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient
from testing.frameworks.python.gh_cli_workflow_run_log_reader import (
    GhCliWorkflowRunLogReader,
)


def create_github_accessibility_log_validation_step_presence_probe(
    repository_root: Path,
    *,
    config_path: Path | None = None,
) -> GitHubAccessibilityPullRequestGateProbe:
    config = GitHubAccessibilityPullRequestGateConfig.from_file(
        config_path or repository_root / "testing/tests/TS-950/config.yaml"
    )
    return GitHubAccessibilityLogValidationStepPresenceProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
    )


def create_github_accessibility_log_validation_step_presence_run_log_reader(
    repository_root: Path,
) -> GitHubWorkflowRunLogReader:
    return GhCliWorkflowRunLogReader(repository_root)

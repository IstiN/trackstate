from __future__ import annotations

from pathlib import Path

from testing.components.services.github_accessibility_missing_placeholder_probe import (
    GitHubAccessibilityMissingPlaceholderProbeService,
)
from testing.components.services.github_accessibility_stage_log_inspector import (
    GitHubAccessibilityStageLogInspector,
)
from testing.core.config.github_accessibility_pull_request_gate_config import (
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient
from testing.frameworks.python.gh_cli_workflow_run_log_reader import (
    GhCliWorkflowRunLogReader,
)


def create_github_accessibility_missing_placeholder_probe(
    repository_root: Path,
    *,
    config_path: Path | None = None,
) -> GitHubAccessibilityPullRequestGateProbe:
    config = GitHubAccessibilityPullRequestGateConfig.from_file(
        config_path or repository_root / "testing/tests/TS-952/config.yaml"
    )
    return GitHubAccessibilityMissingPlaceholderProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
    )


def create_github_accessibility_missing_placeholder_stage_log_inspector(
    repository_root: Path,
) -> GitHubAccessibilityStageLogInspector:
    return GitHubAccessibilityStageLogInspector(
        GhCliWorkflowRunLogReader(repository_root)
    )

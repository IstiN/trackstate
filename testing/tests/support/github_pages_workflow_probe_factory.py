from __future__ import annotations

from pathlib import Path

from testing.components.services.github_pages_workflow_probe import (
    GitHubPagesWorkflowProbe as LiveGitHubPagesWorkflowProbe,
)
from testing.core.interfaces.github_pages_workflow_probe import GitHubPagesWorkflowProbe
from testing.core.models.github_pages_workflow_probe_config import (
    GitHubPagesWorkflowProbeConfig,
)


def create_github_pages_workflow_probe(repository_root: Path) -> GitHubPagesWorkflowProbe:
    config = GitHubPagesWorkflowProbeConfig.from_file(
        repository_root / "testing/tests/TS-69/config.yaml"
    )
    return LiveGitHubPagesWorkflowProbe(repository_root, config)

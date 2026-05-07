from __future__ import annotations

from pathlib import Path

from testing.components.services.github_pages_workflow_probe import (
    GitHubPagesWorkflowProbe as LiveGitHubPagesWorkflowProbe,
)
from testing.core.interfaces.github_pages_workflow_probe import GitHubPagesWorkflowProbe


def create_github_pages_workflow_probe(repository_root: Path) -> GitHubPagesWorkflowProbe:
    return LiveGitHubPagesWorkflowProbe(repository_root)

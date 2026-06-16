from __future__ import annotations

from pathlib import Path

from testing.components.services.github_pages_workflow_probe import (
    GitHubPagesWorkflowProbe as LiveGitHubPagesWorkflowProbe,
)
from testing.core.interfaces.github_pages_workflow_probe import GitHubPagesWorkflowProbe
from testing.core.models.github_pages_workflow_probe_config import (
    GitHubPagesWorkflowProbeConfig,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient
from testing.frameworks.python.urllib_url_text_reader import UrllibUrlTextReader


def create_github_pages_workflow_probe(repository_root: Path) -> GitHubPagesWorkflowProbe:
    config = GitHubPagesWorkflowProbeConfig.from_file(
        repository_root / "testing/tests/TS-69/config.yaml"
    )
    return LiveGitHubPagesWorkflowProbe(
        config,
        github_api_client=GhCliApiClient(repository_root),
        url_text_reader=UrllibUrlTextReader(),
    )

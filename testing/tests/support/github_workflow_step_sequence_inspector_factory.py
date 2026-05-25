from __future__ import annotations

from pathlib import Path

from testing.components.services.github_workflow_step_sequence_inspector import (
    GitHubWorkflowStepSequenceInspectorService,
)
from testing.core.interfaces.github_workflow_step_sequence_inspector import (
    GitHubWorkflowStepSequenceInspector,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient


def create_github_workflow_step_sequence_inspector(
    repository_root: Path,
) -> GitHubWorkflowStepSequenceInspector:
    return GitHubWorkflowStepSequenceInspectorService(
        github_api_client=GhCliApiClient(repository_root),
    )

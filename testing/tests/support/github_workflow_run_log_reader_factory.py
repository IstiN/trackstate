from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.github_workflow_run_log_reader import (
    GitHubWorkflowRunLogReader,
)
from testing.frameworks.python.gh_cli_workflow_run_log_reader import (
    GhCliWorkflowRunLogReader,
)


def create_github_workflow_run_log_reader(
    repository_root: Path,
) -> GitHubWorkflowRunLogReader:
    return GhCliWorkflowRunLogReader(repository_root)

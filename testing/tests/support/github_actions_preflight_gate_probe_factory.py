from __future__ import annotations

from pathlib import Path

from testing.components.services.github_actions_preflight_gate_probe import (
    GitHubActionsPreflightGateProbeService,
)
from testing.core.config.github_actions_preflight_gate_config import (
    GitHubActionsPreflightGateConfig,
)
from testing.core.interfaces.github_actions_preflight_gate_probe import (
    GitHubActionsPreflightGateProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient
from testing.frameworks.python.gh_cli_workflow_run_log_reader import (
    GhCliWorkflowRunLogReader,
)


def create_github_actions_preflight_gate_probe(
    repository_root: Path,
    *,
    config_path: Path | None = None,
) -> GitHubActionsPreflightGateProbe:
    config = GitHubActionsPreflightGateConfig.from_file(
        config_path or repository_root / "testing/tests/TS-706/config.yaml"
    )
    return GitHubActionsPreflightGateProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
        workflow_run_log_reader=GhCliWorkflowRunLogReader(repository_root),
    )

from __future__ import annotations

from pathlib import Path

from testing.components.services.actionlint_non_workflow_pull_request_gate_probe import (
    ActionlintNonWorkflowPullRequestGateProbeService,
)
from testing.core.config.actionlint_non_workflow_pull_request_gate_config import (
    ActionlintNonWorkflowPullRequestGateConfig,
)
from testing.core.interfaces.actionlint_non_workflow_pull_request_gate_probe import (
    ActionlintNonWorkflowPullRequestGateProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient


def create_actionlint_non_workflow_pull_request_gate_probe(
    repository_root: Path,
    *,
    config_path: Path | None = None,
) -> ActionlintNonWorkflowPullRequestGateProbe:
    config = ActionlintNonWorkflowPullRequestGateConfig.from_file(
        config_path or repository_root / "testing/tests/TS-262/config.yaml"
    )
    return ActionlintNonWorkflowPullRequestGateProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
    )

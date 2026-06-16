from __future__ import annotations

from pathlib import Path

from testing.components.services.actionlint_workflow_gate_probe import (
    ActionlintWorkflowGateProbeService,
)
from testing.core.config.actionlint_workflow_gate_config import (
    ActionlintWorkflowGateConfig,
)
from testing.core.interfaces.actionlint_workflow_gate_probe import (
    ActionlintWorkflowGateProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient


def create_actionlint_workflow_gate_probe(
    repository_root: Path,
    *,
    config_path: Path | None = None,
) -> ActionlintWorkflowGateProbe:
    config = ActionlintWorkflowGateConfig.from_file(
        config_path or repository_root / "testing/tests/TS-251/config.yaml"
    )
    return ActionlintWorkflowGateProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
    )

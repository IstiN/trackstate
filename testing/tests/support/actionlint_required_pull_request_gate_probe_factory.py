from __future__ import annotations

from pathlib import Path

from testing.components.services.actionlint_required_pull_request_gate_probe import (
    ActionlintRequiredPullRequestGateProbeService,
)
from testing.core.config.actionlint_required_pull_request_gate_config import (
    ActionlintRequiredPullRequestGateConfig,
)
from testing.core.interfaces.actionlint_required_pull_request_gate_probe import (
    ActionlintRequiredPullRequestGateProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient


def create_actionlint_required_pull_request_gate_probe(
    repository_root: Path,
    *,
    config_path: Path | None = None,
) -> ActionlintRequiredPullRequestGateProbe:
    config = ActionlintRequiredPullRequestGateConfig.from_file(
        config_path or repository_root / "testing/tests/TS-257/config.yaml"
    )
    return ActionlintRequiredPullRequestGateProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
    )

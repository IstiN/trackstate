from __future__ import annotations

from pathlib import Path

from testing.components.services.release_source_workflow_validator import (
    ReleaseSourceWorkflowValidator,
)
from testing.core.config.release_source_workflow_config import (
    ReleaseSourceWorkflowConfig,
)
from testing.core.interfaces.release_source_workflow_probe import (
    ReleaseSourceWorkflowProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient


def create_release_source_workflow_probe(
    repository_root: Path,
) -> ReleaseSourceWorkflowProbe:
    config = ReleaseSourceWorkflowConfig.from_file(
        repository_root / "testing/tests/TS-83/config.yaml"
    )
    return ReleaseSourceWorkflowValidator(
        config,
        github_api_client=GhCliApiClient(repository_root),
    )

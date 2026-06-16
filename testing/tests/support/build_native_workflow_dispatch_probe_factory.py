from __future__ import annotations

from pathlib import Path

from testing.components.services.build_native_workflow_dispatch_probe import (
    BuildNativeWorkflowDispatchProbeService,
)
from testing.core.config.build_native_workflow_dispatch_config import (
    BuildNativeWorkflowDispatchConfig,
)
from testing.core.interfaces.build_native_workflow_dispatch_probe import (
    BuildNativeWorkflowDispatchProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient


def create_build_native_workflow_dispatch_probe(
    repository_root: Path,
) -> BuildNativeWorkflowDispatchProbe:
    config = BuildNativeWorkflowDispatchConfig.from_file(
        repository_root / "testing" / "tests" / "TS-1346" / "config.yaml"
    )
    return BuildNativeWorkflowDispatchProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
    )

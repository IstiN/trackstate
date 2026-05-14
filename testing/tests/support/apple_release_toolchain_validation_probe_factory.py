from __future__ import annotations

from pathlib import Path

from testing.components.services.apple_release_toolchain_validation_probe import (
    AppleReleaseToolchainValidationProbeService,
)
from testing.core.config.apple_release_toolchain_validation_config import (
    AppleReleaseToolchainValidationConfig,
)
from testing.core.interfaces.apple_release_toolchain_validation_probe import (
    AppleReleaseToolchainValidationProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient
from testing.frameworks.python.gh_cli_workflow_run_log_reader import (
    GhCliWorkflowRunLogReader,
)
from testing.tests.support.github_repository_file_page_factory import (
    create_github_repository_file_page,
)


def create_apple_release_toolchain_validation_probe(
    repository_root: Path,
    *,
    screenshot_directory: Path | None = None,
) -> AppleReleaseToolchainValidationProbe:
    config = AppleReleaseToolchainValidationConfig.from_file(
        repository_root / "testing/tests/TS-707/config.yaml"
    )
    return AppleReleaseToolchainValidationProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
        workflow_run_log_reader=GhCliWorkflowRunLogReader(repository_root),
        file_page_factory=create_github_repository_file_page,
        screenshot_directory=screenshot_directory,
    )

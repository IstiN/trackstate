from __future__ import annotations

from pathlib import Path

from testing.components.services.pull_request_release_dry_run_probe import (
    PullRequestReleaseDryRunProbeService,
)
from testing.core.config.pull_request_release_dry_run_config import (
    PullRequestReleaseDryRunConfig,
)
from testing.core.interfaces.pull_request_release_dry_run_probe import (
    PullRequestReleaseDryRunProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient


def create_pull_request_release_dry_run_probe(
    repository_root: Path,
) -> PullRequestReleaseDryRunProbe:
    config = PullRequestReleaseDryRunConfig.from_file(
        repository_root / "testing/tests/TS-250/config.yaml"
    )
    return PullRequestReleaseDryRunProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
    )

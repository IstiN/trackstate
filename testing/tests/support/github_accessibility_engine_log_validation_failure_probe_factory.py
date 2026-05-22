from __future__ import annotations

from pathlib import Path

from testing.components.services.github_accessibility_engine_log_validation_failure_probe import (
    GitHubAccessibilityEngineLogValidationFailureProbeService,
)
from testing.core.config.github_accessibility_pull_request_gate_config import (
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient


def create_github_accessibility_engine_log_validation_failure_probe(
    repository_root: Path,
    *,
    config_path: Path | None = None,
) -> GitHubAccessibilityPullRequestGateProbe:
    config = GitHubAccessibilityPullRequestGateConfig.from_file(
        config_path or repository_root / "testing/tests/TS-943/config.yaml"
    )
    return GitHubAccessibilityEngineLogValidationFailureProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
    )

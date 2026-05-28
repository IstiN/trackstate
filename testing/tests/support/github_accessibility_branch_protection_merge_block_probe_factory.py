from __future__ import annotations

from pathlib import Path

from testing.components.services.github_accessibility_branch_protection_merge_block_probe import (
    GitHubAccessibilityBranchProtectionMergeBlockProbeService,
)
from testing.core.config.github_accessibility_pull_request_gate_config import (
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_branch_protection_merge_block_probe import (
    GitHubAccessibilityBranchProtectionMergeBlockProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient


def create_github_accessibility_branch_protection_merge_block_probe(
    repository_root: Path,
    *,
    config_path: Path | None = None,
) -> GitHubAccessibilityBranchProtectionMergeBlockProbe:
    config = GitHubAccessibilityPullRequestGateConfig.from_file(
        config_path or repository_root / "testing/tests/TS-936/config.yaml"
    )
    return GitHubAccessibilityBranchProtectionMergeBlockProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
    )

from __future__ import annotations

from pathlib import Path

from testing.components.services.github_actions_dependabot_monitor_probe import (
    GitHubActionsDependabotMonitorProbeService,
)
from testing.core.config.github_actions_dependabot_monitor_config import (
    GitHubActionsDependabotMonitorConfig,
)
from testing.core.interfaces.github_actions_dependabot_monitor_probe import (
    GitHubActionsDependabotMonitorProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient
from testing.tests.support.github_repository_file_page_factory import (
    create_github_repository_file_page,
)


def create_github_actions_dependabot_monitor_probe(
    repository_root: Path,
    *,
    config_path: Path | None = None,
    screenshot_path: Path | None = None,
) -> GitHubActionsDependabotMonitorProbe:
    config = GitHubActionsDependabotMonitorConfig.from_file(
        config_path or repository_root / "testing/tests/TS-267/config.yaml"
    )
    return GitHubActionsDependabotMonitorProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
        file_page_factory=create_github_repository_file_page,
        screenshot_path=screenshot_path,
    )

from __future__ import annotations

from pathlib import Path

from testing.components.services.github_release_accessibility_validator import (
    GitHubReleaseAccessibilityValidator,
)
from testing.core.config.github_release_accessibility_config import (
    GitHubReleaseAccessibilityConfig,
)
from testing.core.interfaces.github_release_accessibility_probe import (
    GitHubReleaseAccessibilityProbe,
)
from testing.frameworks.python.urllib_json_array_http_reader import (
    UrllibJsonArrayHttpReader,
)
from testing.tests.support.github_release_page_factory import create_github_release_page


def create_github_release_accessibility_probe(
    repository_root: Path,
) -> GitHubReleaseAccessibilityProbe:
    config = GitHubReleaseAccessibilityConfig.from_file(
        repository_root / "testing/tests/TS-710/config.yaml",
    )
    return GitHubReleaseAccessibilityValidator(
        config,
        json_array_http_reader=UrllibJsonArrayHttpReader(),
        release_page_factory=create_github_release_page,
    )

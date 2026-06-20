from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.github_release_tag_resolver import (
    GitHubReleaseTagResolver,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient
from testing.frameworks.python.github_release_tag_resolver import (
    PythonGitHubReleaseTagResolver,
)


def create_github_release_tag_resolver(
    repository_root: Path | None = None,
) -> GitHubReleaseTagResolver:
    if repository_root is None:
        repository_root = Path(__file__).resolve().parents[3]
    return PythonGitHubReleaseTagResolver(
        github_api_client=GhCliApiClient(repository_root),
    )

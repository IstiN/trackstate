from __future__ import annotations

from testing.components.pages.github_repository_directory_page import (
    GitHubRepositoryDirectoryPage,
)
from testing.frameworks.python.urllib_url_text_reader import UrllibUrlTextReader


def create_github_repository_directory_page() -> GitHubRepositoryDirectoryPage:
    return GitHubRepositoryDirectoryPage(UrllibUrlTextReader())

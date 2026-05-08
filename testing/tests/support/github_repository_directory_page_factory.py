from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Callable

from testing.components.pages.github_repository_directory_page import (
    GitHubRepositoryDirectoryPage,
)
from testing.core.interfaces.web_app_session import WebAppSession
from testing.frameworks.python.playwright_web_app_session import PlaywrightWebAppRuntime

WebAppRuntimeFactory = Callable[[], AbstractContextManager[WebAppSession]]


class GitHubRepositoryDirectoryPageContext(
    AbstractContextManager[GitHubRepositoryDirectoryPage]
):
    def __init__(
        self,
        runtime_factory: WebAppRuntimeFactory = PlaywrightWebAppRuntime,
    ) -> None:
        self._runtime_factory = runtime_factory
        self._runtime: AbstractContextManager[WebAppSession] | None = None

    def __enter__(self) -> GitHubRepositoryDirectoryPage:
        self._runtime = self._runtime_factory()
        session = self._runtime.__enter__()
        return GitHubRepositoryDirectoryPage(session)

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._runtime is None:
            return None
        return self._runtime.__exit__(exc_type, exc, exc_tb)


def create_github_repository_directory_page(
    *,
    runtime_factory: WebAppRuntimeFactory = PlaywrightWebAppRuntime,
) -> GitHubRepositoryDirectoryPageContext:
    return GitHubRepositoryDirectoryPageContext(runtime_factory=runtime_factory)

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Callable

from testing.components.pages.github_repository_file_page import (
    GitHubRepositoryFilePage,
)
from testing.core.interfaces.web_app_session import WebAppSession
from testing.frameworks.python.urllib_web_app_session import UrllibWebAppRuntime

WebAppRuntimeFactory = Callable[[], AbstractContextManager[WebAppSession]]


class GitHubRepositoryFilePageContext(AbstractContextManager[GitHubRepositoryFilePage]):
    def __init__(
        self,
        runtime_factory: WebAppRuntimeFactory | None = None,
    ) -> None:
        self._runtime_factory = runtime_factory or _default_runtime_factory
        self._runtime: AbstractContextManager[WebAppSession] | None = None

    def __enter__(self) -> GitHubRepositoryFilePage:
        self._runtime = self._runtime_factory()
        session = self._runtime.__enter__()
        return GitHubRepositoryFilePage(session)

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._runtime is None:
            return None
        return self._runtime.__exit__(exc_type, exc, exc_tb)


def create_github_repository_file_page(
    *,
    runtime_factory: WebAppRuntimeFactory | None = None,
) -> GitHubRepositoryFilePageContext:
    return GitHubRepositoryFilePageContext(runtime_factory=runtime_factory)


def _default_runtime_factory() -> AbstractContextManager[WebAppSession]:
    try:
        from testing.frameworks.python.playwright_web_app_session import (
            PlaywrightWebAppRuntime,
        )

        return PlaywrightWebAppRuntime()
    except ModuleNotFoundError:
        return UrllibWebAppRuntime()

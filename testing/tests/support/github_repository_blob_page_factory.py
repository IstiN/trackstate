from __future__ import annotations

from contextlib import AbstractContextManager

from testing.components.pages.github_repository_blob_page import (
    GitHubRepositoryBlobPage,
)
from testing.core.interfaces.web_app_session import WebAppSession
from testing.tests.support.github_pull_request_compose_page_factory import (
    GitHubPullRequestComposeRuntimeUnavailableError,
    WebAppRuntimeFactory,
    _default_runtime_factory,
)


class GitHubRepositoryBlobPageContext(
    AbstractContextManager[GitHubRepositoryBlobPage]
):
    def __init__(
        self,
        runtime_factory: WebAppRuntimeFactory | None = None,
    ) -> None:
        self._runtime_factory = runtime_factory or _default_runtime_factory
        self._runtime: AbstractContextManager[WebAppSession] | None = None

    def __enter__(self) -> GitHubRepositoryBlobPage:
        self._runtime = self._runtime_factory()
        session = self._runtime.__enter__()
        return GitHubRepositoryBlobPage(session)

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._runtime is None:
            return None
        return self._runtime.__exit__(exc_type, exc, exc_tb)


def create_github_repository_blob_page(
    *,
    runtime_factory: WebAppRuntimeFactory | None = None,
) -> GitHubRepositoryBlobPageContext:
    return GitHubRepositoryBlobPageContext(runtime_factory=runtime_factory)


__all__ = [
    "GitHubPullRequestComposeRuntimeUnavailableError",
    "GitHubRepositoryBlobPageContext",
    "create_github_repository_blob_page",
]

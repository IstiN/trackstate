from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Callable

from testing.components.pages.github_pull_request_compose_page import (
    GitHubPullRequestComposePage,
)
from testing.core.interfaces.web_app_session import WebAppSession

WebAppRuntimeFactory = Callable[[], AbstractContextManager[WebAppSession]]


class GitHubPullRequestComposeRuntimeUnavailableError(RuntimeError):
    """Raised when TS-909 cannot create a browser runtime that can prove the flow."""


class GitHubPullRequestComposePageContext(
    AbstractContextManager[GitHubPullRequestComposePage]
):
    def __init__(
        self,
        runtime_factory: WebAppRuntimeFactory | None = None,
    ) -> None:
        self._runtime_factory = runtime_factory or _default_runtime_factory
        self._runtime: AbstractContextManager[WebAppSession] | None = None

    def __enter__(self) -> GitHubPullRequestComposePage:
        self._runtime = self._runtime_factory()
        session = self._runtime.__enter__()
        return GitHubPullRequestComposePage(session)

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._runtime is None:
            return None
        return self._runtime.__exit__(exc_type, exc, exc_tb)


def create_github_pull_request_compose_page(
    *,
    runtime_factory: WebAppRuntimeFactory | None = None,
) -> GitHubPullRequestComposePageContext:
    return GitHubPullRequestComposePageContext(runtime_factory=runtime_factory)


def _default_runtime_factory() -> AbstractContextManager[WebAppSession]:
    try:
        from testing.frameworks.python.playwright_web_app_session import (
            PlaywrightWebAppRuntime,
        )

        return PlaywrightWebAppRuntime()
    except ModuleNotFoundError:
        raise GitHubPullRequestComposeRuntimeUnavailableError(
            "TS-909 requires a Playwright browser runtime to verify GitHub's live "
            "pull-request compose form. Install Playwright and Chromium before "
            "running this test; the unauthenticated urllib fallback is not a "
            "valid proof source for the PR body."
        ) from None

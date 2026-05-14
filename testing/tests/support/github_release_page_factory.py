from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Callable

from testing.components.pages.github_release_page import GitHubReleasePage
from testing.core.interfaces.web_app_session import WebAppSession

WebAppRuntimeFactory = Callable[[], AbstractContextManager[WebAppSession]]


class GitHubReleasePageContext(AbstractContextManager[GitHubReleasePage]):
    def __init__(
        self,
        *,
        runtime_factory: WebAppRuntimeFactory | None = None,
    ) -> None:
        self._runtime_factory = runtime_factory or _default_runtime_factory
        self._runtime: AbstractContextManager[WebAppSession] | None = None

    def __enter__(self) -> GitHubReleasePage:
        self._runtime = self._runtime_factory()
        session = self._runtime.__enter__()
        return GitHubReleasePage(session)

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._runtime is None:
            return None
        return self._runtime.__exit__(exc_type, exc, exc_tb)


def create_github_release_page(
    *,
    runtime_factory: WebAppRuntimeFactory | None = None,
) -> GitHubReleasePageContext:
    return GitHubReleasePageContext(runtime_factory=runtime_factory)


def _default_runtime_factory() -> AbstractContextManager[WebAppSession]:
    try:
        from testing.frameworks.python.playwright_web_app_session import (
            PlaywrightWebAppRuntime,
        )
    except ModuleNotFoundError as error:
        raise AssertionError(
            "Playwright browser verification is required for TS-710 GitHub release "
            "accessibility checks, but the Playwright runtime is not available in "
            "this environment.",
        ) from error
    return PlaywrightWebAppRuntime()

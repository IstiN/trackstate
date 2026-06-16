from __future__ import annotations

import os
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

        auth_session_path = os.environ.get("GITHUB_BROWSER_AUTH_SESSION")
        if auth_session_path:
            return _AuthenticatedPlaywrightWebAppRuntime(
                storage_state_path=auth_session_path,
            )
        return PlaywrightWebAppRuntime()
    except ModuleNotFoundError:
        raise GitHubPullRequestComposeRuntimeUnavailableError(
            "TS-909 requires a Playwright browser runtime to verify GitHub's live "
            "pull-request compose form. Install Playwright and Chromium before "
            "running this test; the unauthenticated urllib fallback is not a "
            "valid proof source for the PR body."
        ) from None


class _AuthenticatedPlaywrightWebAppRuntime(
    AbstractContextManager[WebAppSession],
):
    """Playwright runtime that loads a pre-saved GitHub auth storage state."""

    def __init__(
        self,
        *,
        storage_state_path: str,
        viewport_width: int = 1440,
        viewport_height: int = 960,
    ) -> None:
        self._storage_state_path = storage_state_path
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._viewport_width = viewport_width
        self._viewport_height = viewport_height

    def __enter__(self) -> WebAppSession:
        from pathlib import Path
        from playwright.sync_api import sync_playwright
        from testing.frameworks.python.playwright_web_app_session import (
            PlaywrightWebAppSession,
            _CHROMIUM_FOREGROUND_TIMING_ARGS,
        )

        state_path = Path(self._storage_state_path)
        if not state_path.exists():
            raise GitHubPullRequestComposeRuntimeUnavailableError(
                f"GITHUB_BROWSER_AUTH_SESSION points to a missing file: {state_path}\n"
                "Generate it by logging into github.com via a browser and exporting "
                "cookies, or run testing/scripts/export_github_auth.py to create it."
            )

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=True,
            args=_CHROMIUM_FOREGROUND_TIMING_ARGS,
        )
        self._context = self._browser.new_context(
            viewport={
                "width": self._viewport_width,
                "height": self._viewport_height,
            },
            storage_state=str(state_path),
        )
        self._page = self._context.new_page()
        return PlaywrightWebAppSession(self._page)

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        return None

from __future__ import annotations

from contextlib import AbstractContextManager
import json

from playwright.sync_api import Browser, BrowserContext, Page, Route, sync_playwright

from testing.frameworks.python.playwright_web_app_session import PlaywrightWebAppSession


class StartupRecoveryRateLimitObservation:
    def __init__(self, *, blocked_repository_path: str) -> None:
        self.blocked_repository_path = blocked_repository_path
        self.blocked_urls: list[str] = []

    @property
    def blocked_was_exercised(self) -> bool:
        return len(self.blocked_urls) > 0


class StartupRecoveryRateLimitRuntime(
    AbstractContextManager[PlaywrightWebAppSession],
):
    def __init__(
        self,
        *,
        observation: StartupRecoveryRateLimitObservation,
        failure_message: str,
        retry_after_seconds: int = 60,
    ) -> None:
        self._observation = observation
        self._failure_message = failure_message
        self._retry_after_seconds = retry_after_seconds
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def __enter__(self) -> PlaywrightWebAppSession:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._context = self._browser.new_context(viewport={"width": 1440, "height": 1200})
        self._context.route("https://api.github.com/**", self._handle_github_api_route)
        self._page = self._context.new_page()
        return PlaywrightWebAppSession(self._page)

    def _handle_github_api_route(self, route: Route) -> None:
        url = route.request.url
        if f"/contents/{self._observation.blocked_repository_path}" in url:
            self._observation.blocked_urls.append(url)
            route.fulfill(
                status=403,
                content_type="application/json",
                body=json.dumps(
                    {
                        "message": self._failure_message,
                        "documentation_url": (
                            "https://docs.github.com/rest/overview/resources-in-the-rest-api"
                            "#rate-limiting"
                        ),
                    },
                ),
                headers={
                    "x-ratelimit-remaining": "0",
                    "retry-after": str(self._retry_after_seconds),
                },
            )
            return
        route.continue_()

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        return None


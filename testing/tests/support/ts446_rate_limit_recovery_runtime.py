from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass, field
import json

from playwright.sync_api import Browser, BrowserContext, Page, Route, sync_playwright

from testing.frameworks.python.playwright_web_app_session import PlaywrightWebAppSession


@dataclass
class RateLimitBootstrapObservation:
    repository: str
    ref: str
    blocked_path: str = "DEMO/.trackstate/index/issues.json"
    bootstrap_urls: list[str] = field(default_factory=list)
    blocked_urls: list[str] = field(default_factory=list)

    @property
    def blocked_target_url(self) -> str:
        return (
            f"https://api.github.com/repos/{self.repository}/contents/"
            f"{self.blocked_path}?ref={self.ref}"
        )

    @property
    def bootstrap_request_count(self) -> int:
        return len(self.bootstrap_urls)

    @property
    def blocked_request_count(self) -> int:
        return len(self.blocked_urls)

    def tracks_bootstrap_url(self, url: str) -> bool:
        return url.startswith(f"https://api.github.com/repos/{self.repository}/")


class RateLimitRecoveryRuntime(AbstractContextManager[PlaywrightWebAppSession]):
    def __init__(self, *, observation: RateLimitBootstrapObservation) -> None:
        self._observation = observation
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def __enter__(self) -> PlaywrightWebAppSession:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._context = self._browser.new_context(viewport={"width": 1440, "height": 960})
        self._context.route("https://api.github.com/**", self._handle_github_api_route)
        self._page = self._context.new_page()
        return PlaywrightWebAppSession(self._page)

    def _handle_github_api_route(self, route: Route) -> None:
        url = route.request.url
        if not self._observation.tracks_bootstrap_url(url):
            route.continue_()
            return

        self._observation.bootstrap_urls.append(url)
        if url == self._observation.blocked_target_url:
            self._observation.blocked_urls.append(url)
            route.fulfill(
                status=403,
                content_type="application/json",
                body=json.dumps(
                    {
                        "message": "API rate limit exceeded",
                        "documentation_url": (
                            "https://docs.github.com/rest/overview/resources-in-the-rest-api"
                            "#rate-limiting"
                        ),
                    }
                ),
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

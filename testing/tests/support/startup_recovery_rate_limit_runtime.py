from __future__ import annotations

from contextlib import AbstractContextManager
import json
import time
from dataclasses import dataclass, field
from threading import Lock

from playwright.sync_api import Browser, BrowserContext, Page, Route, sync_playwright

from testing.frameworks.python.playwright_web_app_session import PlaywrightWebAppSession


@dataclass(frozen=True)
class StartupRecoveryObservedEvent:
    observed_order: int
    observed_at_monotonic: float


@dataclass(frozen=True)
class StartupRecoveryBlockedRequestObservation(StartupRecoveryObservedEvent):
    url: str


@dataclass
class StartupRecoveryRateLimitObservation:
    blocked_repository_path: str
    blocked_requests: list[StartupRecoveryBlockedRequestObservation] = field(
        default_factory=list,
    )
    shell_ready_event: StartupRecoveryObservedEvent | None = None
    _next_observed_order: int = field(default=1, init=False, repr=False)
    _event_lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def record_blocked_request(self, url: str) -> StartupRecoveryBlockedRequestObservation:
        observation = StartupRecoveryBlockedRequestObservation(
            url=url,
            **self._reserve_event_payload(),
        )
        self.blocked_requests.append(observation)
        return observation

    def record_shell_ready(self) -> StartupRecoveryObservedEvent:
        if self.shell_ready_event is not None:
            return self.shell_ready_event
        self.shell_ready_event = StartupRecoveryObservedEvent(
            **self._reserve_event_payload(),
        )
        return self.shell_ready_event

    def _reserve_event_payload(self) -> dict[str, float | int]:
        with self._event_lock:
            observed_order = self._next_observed_order
            self._next_observed_order += 1
        return {
            "observed_order": observed_order,
            "observed_at_monotonic": time.monotonic(),
        }

    @property
    def blocked_was_exercised(self) -> bool:
        return len(self.blocked_requests) > 0

    @property
    def blocked_urls(self) -> list[str]:
        return [request.url for request in self.blocked_requests]


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
            self._observation.record_blocked_request(url)
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

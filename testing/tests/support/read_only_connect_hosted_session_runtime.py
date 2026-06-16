from __future__ import annotations

import json
from dataclasses import dataclass, field
from urllib.parse import urlparse

from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightStoredTokenWebAppRuntime,
    PlaywrightWebAppSession,
    sync_playwright,
)


@dataclass
class ReadOnlyConnectHostedSessionObservation:
    repository: str
    intercepted_urls: list[str] = field(default_factory=list)
    observed_permissions: list[dict[str, object]] = field(default_factory=list)

    @property
    def repo_endpoint(self) -> str:
        return f"/repos/{self.repository}"

    @property
    def was_exercised(self) -> bool:
        return bool(self.intercepted_urls)


class ReadOnlyConnectHostedSessionRuntime(PlaywrightStoredTokenWebAppRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        observation: ReadOnlyConnectHostedSessionObservation,
    ) -> None:
        super().__init__(repository=repository, token=token)
        self._observation = observation

    def __enter__(self) -> PlaywrightWebAppSession:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._context = self._browser.new_context(viewport={"width": 1440, "height": 960})
        self._context.route("https://api.github.com/**", self._handle_github_api_route)
        self._page = self._context.new_page()
        return PlaywrightWebAppSession(self._page)

    def _handle_github_api_route(self, route) -> None:
        request = route.request
        parsed = urlparse(request.url)
        if request.method.upper() != "GET" or parsed.path != self._observation.repo_endpoint:
            self._continue_github_api_route(route)
            return

        fetched = route.fetch(headers=self._authorized_github_headers(request.headers))
        payload = fetched.json()
        if not isinstance(payload, dict):
            route.fulfill(status=fetched.status, body=fetched.text())
            return

        permissions = payload.get("permissions")
        original_permissions = permissions if isinstance(permissions, dict) else {}
        read_only_permissions = {
            **original_permissions,
            "pull": True,
            "push": False,
            "admin": False,
        }
        patched_payload = {
            **payload,
            "permissions": read_only_permissions,
        }
        self._observation.intercepted_urls.append(request.url)
        self._observation.observed_permissions.append(
            {
                "original": dict(original_permissions),
                "patched": dict(read_only_permissions),
            },
        )
        route.fulfill(
            status=fetched.status,
            headers={
                key: value
                for key, value in fetched.headers.items()
                if key.lower() != "content-length"
            },
            content_type="application/json",
            body=json.dumps(patched_payload),
        )

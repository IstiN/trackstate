from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass, field
import json
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Browser, BrowserContext, Page, Route, sync_playwright

from testing.frameworks.python.playwright_web_app_session import PlaywrightWebAppSession


@dataclass
class MissingIndexBootstrapObservation:
    repository: str
    ref: str
    blocked_path: str = "DEMO/.trackstate/index/issues.json"
    bootstrap_urls: list[str] = field(default_factory=list)
    tree_urls: list[str] = field(default_factory=list)
    modified_tree_urls: list[str] = field(default_factory=list)
    blocked_index_urls: list[str] = field(default_factory=list)
    issue_content_urls: list[str] = field(default_factory=list)
    other_content_urls: list[str] = field(default_factory=list)

    @property
    def blocked_target_url(self) -> str:
        return (
            f"https://api.github.com/repos/{self.repository}/contents/"
            f"{self.blocked_path}?ref={self.ref}"
        )

    @property
    def bootstrap_request_count(self) -> int:
        return len(self.bootstrap_urls)

    def tracks_repository_url(self, url: str) -> bool:
        return url.startswith(f"https://api.github.com/repos/{self.repository}/")


class Ts422MissingIndexRuntime(AbstractContextManager[PlaywrightWebAppSession]):
    def __init__(self, *, observation: MissingIndexBootstrapObservation) -> None:
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
        if not self._observation.tracks_repository_url(url):
            route.continue_()
            return

        self._observation.bootstrap_urls.append(url)
        if self._is_recursive_tree_url(url):
            self._observation.tree_urls.append(url)
            fetched = route.fetch()
            payload = fetched.json()
            if not isinstance(payload, dict):
                route.fulfill(status=fetched.status, body=fetched.text())
                return
            tree = payload.get("tree")
            if isinstance(tree, list):
                filtered_tree = [
                    entry
                    for entry in tree
                    if not (
                        isinstance(entry, dict)
                        and entry.get("path") == self._observation.blocked_path
                    )
                ]
                if len(filtered_tree) != len(tree):
                    self._observation.modified_tree_urls.append(url)
                    payload = {**payload, "tree": filtered_tree}
            route.fulfill(
                status=fetched.status,
                headers={
                    key: value
                    for key, value in fetched.headers.items()
                    if key.lower() != "content-length"
                },
                content_type="application/json",
                body=json.dumps(payload),
            )
            return

        if url == self._observation.blocked_target_url:
            self._observation.blocked_index_urls.append(url)
            route.fulfill(
                status=404,
                content_type="application/json",
                body=json.dumps({"message": "Not Found"}),
            )
            return

        if self._is_issue_content_url(url):
            self._observation.issue_content_urls.append(url)
        elif "/contents/" in url:
            self._observation.other_content_urls.append(url)

        route.continue_()

    def _is_recursive_tree_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return (
            parsed.path.startswith(f"/repos/{self._observation.repository}/git/trees/")
            and parse_qs(parsed.query).get("recursive") == ["1"]
        )

    def _is_issue_content_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return (
            parsed.path.startswith(f"/repos/{self._observation.repository}/contents/")
            and parsed.path.endswith("/main.md")
        )

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        return None

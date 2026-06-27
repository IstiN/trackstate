from __future__ import annotations

import base64
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
import json
from urllib.parse import parse_qs, urlsplit

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

    @property
    def data_root(self) -> str:
        if "/.trackstate/" in self.blocked_path:
            return self.blocked_path.split("/.trackstate/")[0]
        return ""


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
        self._page.on("request", self._handle_request)
        return PlaywrightWebAppSession(self._page)

    def _handle_request(self, request: object) -> None:
        url = request.url
        if not self._observation.tracks_bootstrap_url(url):
            return
        if self._is_blocked_request(url):
            self._observation.blocked_urls.append(url)

    def _handle_github_api_route(self, route: Route) -> None:
        url = route.request.url
        if not self._observation.tracks_bootstrap_url(url):
            route.continue_()
            return

        self._observation.bootstrap_urls.append(url)
        if self._is_blocked_request(url):
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

        path = urlsplit(url).path
        stub = self._bootstrap_stub_response(path)
        if stub is not None:
            route.fulfill(status=200, content_type="application/json", body=json.dumps(stub))
            return
        route.continue_()

    def _is_blocked_request(self, url: str) -> bool:
        parsed = urlsplit(url)
        expected_path_suffix = f"/contents/{self._observation.blocked_path}"
        if parsed.scheme != "https" or parsed.netloc != "api.github.com":
            return False
        if not parsed.path.endswith(expected_path_suffix):
            return False
        query = parse_qs(parsed.query)
        return query.get("ref") == [self._observation.ref]

    def _bootstrap_stub_response(self, path: str) -> object | None:
        repo = self._observation.repository
        ref = self._observation.ref
        root = self._observation.data_root
        prefix = f"/repos/{repo}/"
        if not path.startswith(prefix):
            return None
        path = path[len(prefix) :]

        if path == f"git/trees/{ref}":
            tree_entries = [
                {"path": _join(root, "project.json"), "type": "blob"},
                {"path": _join(root, "config", "issue-types.json"), "type": "blob"},
                {"path": _join(root, "config", "statuses.json"), "type": "blob"},
                {"path": _join(root, "config", "fields.json"), "type": "blob"},
                {"path": _join(root, "config", "workflows.json"), "type": "blob"},
                {"path": _join(root, "config", "priorities.json"), "type": "blob"},
                {"path": _join(root, ".trackstate", "index", "issues.json"), "type": "blob"},
                {"path": _join(root, "DEMO-1", "main.md"), "type": "blob"},
            ]
            return {"tree": [entry for entry in tree_entries if entry["path"]]}

        if path == f"contents/{_join(root, 'project.json')}":
            return _content({"key": "DEMO", "name": "Demo", "defaultLocale": "en"})
        if path == f"contents/{_join(root, 'config', 'issue-types.json')}":
            return _content(
                [
                    {
                        "id": "story",
                        "name": "Story",
                        "workflowId": "default",
                        "hierarchyLevel": 0,
                    }
                ]
            )
        if path == f"contents/{_join(root, 'config', 'statuses.json')}":
            return _content([{"id": "todo", "name": "To Do", "category": "new"}])
        if path == f"contents/{_join(root, 'config', 'fields.json')}":
            return _content(
                [
                    {
                        "id": "summary",
                        "name": "Summary",
                        "type": "string",
                        "required": True,
                        "reserved": True,
                    }
                ]
            )
        if path == f"contents/{_join(root, 'config', 'workflows.json')}":
            return _content(
                {
                    "default": {
                        "name": "Default",
                        "statuses": ["todo"],
                        "transitions": [],
                    }
                }
            )
        if path == f"contents/{_join(root, 'config', 'priorities.json')}":
            return _content([])
        if path == f"contents/{_join(root, 'config', 'components.json')}":
            return _content([])
        if path == f"contents/{_join(root, 'config', 'versions.json')}":
            return _content([])
        if path == f"contents/{_join(root, 'config', 'resolutions.json')}":
            return _content([])
        if path == f"contents/{_join(root, 'DEMO-1', 'main.md')}":
            return _content("---\nkey: DEMO-1\nproject: DEMO\nissueType: Story\nstatus: todo\n---\n# Summary\nDemo issue.")
        return None

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        return None


def _join(*parts: str) -> str:
    return "/".join(part for part in parts if part)


def _content(payload: object) -> dict[str, object]:
    return {
        "content": base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii"),
        "sha": "stub-sha",
    }

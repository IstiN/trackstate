from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import parse_qs, unquote, urlparse

from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightStoredTokenWebAppRuntime,
)


@dataclass
class HostedBootstrapReadObservation:
    repository: str
    ref: str
    project_path: str
    tree_urls: list[str] = field(default_factory=list)
    project_json_urls: list[str] = field(default_factory=list)
    config_json_urls: list[str] = field(default_factory=list)
    issues_index_urls: list[str] = field(default_factory=list)
    tombstone_metadata_urls: list[str] = field(default_factory=list)
    main_markdown_urls: list[str] = field(default_factory=list)
    comments_urls: list[str] = field(default_factory=list)
    attachments_urls: list[str] = field(default_factory=list)
    other_content_urls: list[str] = field(default_factory=list)

    def tracks_repository_url(self, url: str) -> bool:
        return url.startswith(f"https://api.github.com/repos/{self.repository}/")

    @property
    def all_content_paths(self) -> list[str]:
        paths: list[str] = []
        for collection in (
            self.project_json_urls,
            self.config_json_urls,
            self.issues_index_urls,
            self.tombstone_metadata_urls,
            self.main_markdown_urls,
            self.comments_urls,
            self.attachments_urls,
            self.other_content_urls,
        ):
            for url in collection:
                normalized = self.normalize_content_path(url)
                if normalized is not None:
                    paths.append(normalized)
        return paths

    def normalize_content_path(self, url: str) -> str | None:
        parsed = urlparse(url)
        prefix = f"/repos/{self.repository}/contents/"
        if not parsed.path.startswith(prefix):
            return None
        return unquote(parsed.path.removeprefix(prefix))

    def record_content_url(self, url: str) -> None:
        normalized_path = self.normalize_content_path(url)
        if normalized_path is None:
            return
        if normalized_path == f"{self.project_path}/project.json":
            self.project_json_urls.append(url)
            return
        if normalized_path == f"{self.project_path}/.trackstate/index/issues.json":
            self.issues_index_urls.append(url)
            return
        if normalized_path.startswith(f"{self.project_path}/config/") and normalized_path.endswith(
            ".json",
        ):
            self.config_json_urls.append(url)
            return
        if normalized_path.startswith(f"{self.project_path}/.trackstate/"):
            self.tombstone_metadata_urls.append(url)
            return
        if normalized_path.endswith("/main.md"):
            self.main_markdown_urls.append(url)
            return
        if "/comments/" in normalized_path or normalized_path.endswith("/comments"):
            self.comments_urls.append(url)
            return
        if "/attachments/" in normalized_path or normalized_path.endswith("/attachments"):
            self.attachments_urls.append(url)
            return
        self.other_content_urls.append(url)


class Ts419BootstrapRequestRuntime(PlaywrightStoredTokenWebAppRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        observation: HostedBootstrapReadObservation,
    ) -> None:
        super().__init__(repository=repository, token=token)
        self._observation = observation

    @property
    def observation(self) -> HostedBootstrapReadObservation:
        return self._observation

    def _handle_github_api_route(self, route) -> None:
        url = route.request.url
        if not self._observation.tracks_repository_url(url):
            self._continue_github_api_route(route)
            return
        if self._is_recursive_tree_url(url):
            self._observation.tree_urls.append(url)
        elif "/contents/" in url:
            self._observation.record_content_url(url)
        self._continue_github_api_route(route)

    def _is_recursive_tree_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return (
            parsed.path.startswith(f"/repos/{self._observation.repository}/git/trees/")
            and parse_qs(parsed.query).get("recursive") == ["1"]
        )

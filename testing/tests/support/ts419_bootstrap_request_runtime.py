from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from urllib.parse import parse_qs, unquote, urlparse

from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightStoredTokenWebAppRuntime,
)


@dataclass(frozen=True)
class ObservedRequest:
    url: str
    observed_at_monotonic: float


@dataclass
class HostedBootstrapReadObservation:
    repository: str
    ref: str
    project_path: str
    startup_started_monotonic: float | None = None
    _tree_requests: list[ObservedRequest] = field(default_factory=list)
    _project_json_requests: list[ObservedRequest] = field(default_factory=list)
    _config_json_requests: list[ObservedRequest] = field(default_factory=list)
    _issues_index_requests: list[ObservedRequest] = field(default_factory=list)
    _tombstone_metadata_requests: list[ObservedRequest] = field(default_factory=list)
    _main_markdown_requests: list[ObservedRequest] = field(default_factory=list)
    _comments_requests: list[ObservedRequest] = field(default_factory=list)
    _attachments_requests: list[ObservedRequest] = field(default_factory=list)
    _other_content_requests: list[ObservedRequest] = field(default_factory=list)

    def tracks_repository_url(self, url: str) -> bool:
        return url.startswith(f"https://api.github.com/repos/{self.repository}/")

    @property
    def all_content_paths(self) -> list[str]:
        paths: list[str] = []
        for collection in (
            self._project_json_requests,
            self._config_json_requests,
            self._issues_index_requests,
            self._tombstone_metadata_requests,
            self._main_markdown_requests,
            self._comments_requests,
            self._attachments_requests,
            self._other_content_requests,
        ):
            for request in collection:
                normalized = self.normalize_content_path(request.url)
                if normalized is not None:
                    paths.append(normalized)
        return paths

    @property
    def tree_urls(self) -> list[str]:
        return self._urls(self._tree_requests)

    @property
    def project_json_urls(self) -> list[str]:
        return self._urls(self._project_json_requests)

    @property
    def config_json_urls(self) -> list[str]:
        return self._urls(self._config_json_requests)

    @property
    def issues_index_urls(self) -> list[str]:
        return self._urls(self._issues_index_requests)

    @property
    def tombstone_metadata_urls(self) -> list[str]:
        return self._urls(self._tombstone_metadata_requests)

    @property
    def main_markdown_urls(self) -> list[str]:
        return self._urls(self._main_markdown_requests)

    @property
    def comments_urls(self) -> list[str]:
        return self._urls(self._comments_requests)

    @property
    def attachments_urls(self) -> list[str]:
        return self._urls(self._attachments_requests)

    @property
    def other_content_urls(self) -> list[str]:
        return self._urls(self._other_content_requests)

    def normalize_content_path(self, url: str) -> str | None:
        parsed = urlparse(url)
        prefix = f"/repos/{self.repository}/contents/"
        if not parsed.path.startswith(prefix):
            return None
        return unquote(parsed.path.removeprefix(prefix))

    def record_tree_url(self, url: str, *, observed_at_monotonic: float) -> None:
        self._append_request(self._tree_requests, url, observed_at_monotonic=observed_at_monotonic)

    def record_content_url(self, url: str, *, observed_at_monotonic: float) -> None:
        normalized_path = self.normalize_content_path(url)
        if normalized_path is None:
            return
        if normalized_path == f"{self.project_path}/project.json":
            self._append_request(
                self._project_json_requests,
                url,
                observed_at_monotonic=observed_at_monotonic,
            )
            return
        if normalized_path == f"{self.project_path}/.trackstate/index/issues.json":
            self._append_request(
                self._issues_index_requests,
                url,
                observed_at_monotonic=observed_at_monotonic,
            )
            return
        if normalized_path.startswith(f"{self.project_path}/config/") and normalized_path.endswith(
            ".json",
        ):
            self._append_request(
                self._config_json_requests,
                url,
                observed_at_monotonic=observed_at_monotonic,
            )
            return
        if normalized_path.startswith(f"{self.project_path}/.trackstate/"):
            self._append_request(
                self._tombstone_metadata_requests,
                url,
                observed_at_monotonic=observed_at_monotonic,
            )
            return
        if normalized_path.endswith("/main.md"):
            self._append_request(
                self._main_markdown_requests,
                url,
                observed_at_monotonic=observed_at_monotonic,
            )
            return
        if "/comments/" in normalized_path or normalized_path.endswith("/comments"):
            self._append_request(
                self._comments_requests,
                url,
                observed_at_monotonic=observed_at_monotonic,
            )
            return
        if "/attachments/" in normalized_path or normalized_path.endswith("/attachments"):
            self._append_request(
                self._attachments_requests,
                url,
                observed_at_monotonic=observed_at_monotonic,
            )
            return
        self._append_request(
            self._other_content_requests,
            url,
            observed_at_monotonic=observed_at_monotonic,
        )

    def startup_tree_urls(self, *, within_seconds: float) -> list[str]:
        return self._startup_urls(self._tree_requests, within_seconds=within_seconds)

    def startup_project_json_urls(self, *, within_seconds: float) -> list[str]:
        return self._startup_urls(self._project_json_requests, within_seconds=within_seconds)

    def startup_config_json_urls(self, *, within_seconds: float) -> list[str]:
        return self._startup_urls(self._config_json_requests, within_seconds=within_seconds)

    def startup_issues_index_urls(self, *, within_seconds: float) -> list[str]:
        return self._startup_urls(self._issues_index_requests, within_seconds=within_seconds)

    def startup_tombstone_metadata_urls(self, *, within_seconds: float) -> list[str]:
        return self._startup_urls(self._tombstone_metadata_requests, within_seconds=within_seconds)

    def startup_main_markdown_urls(self, *, within_seconds: float) -> list[str]:
        return self._startup_urls(self._main_markdown_requests, within_seconds=within_seconds)

    def startup_comments_urls(self, *, within_seconds: float) -> list[str]:
        return self._startup_urls(self._comments_requests, within_seconds=within_seconds)

    def startup_attachments_urls(self, *, within_seconds: float) -> list[str]:
        return self._startup_urls(self._attachments_requests, within_seconds=within_seconds)

    def startup_other_content_urls(self, *, within_seconds: float) -> list[str]:
        return self._startup_urls(self._other_content_requests, within_seconds=within_seconds)

    def startup_all_content_paths(self, *, within_seconds: float) -> list[str]:
        paths: list[str] = []
        for collection in (
            self._project_json_requests,
            self._config_json_requests,
            self._issues_index_requests,
            self._tombstone_metadata_requests,
            self._main_markdown_requests,
            self._comments_requests,
            self._attachments_requests,
            self._other_content_requests,
        ):
            for url in self._startup_urls(collection, within_seconds=within_seconds):
                normalized = self.normalize_content_path(url)
                if normalized is not None:
                    paths.append(normalized)
        return paths

    @staticmethod
    def _append_request(
        collection: list[ObservedRequest],
        url: str,
        *,
        observed_at_monotonic: float,
    ) -> None:
        collection.append(
            ObservedRequest(
                url=url,
                observed_at_monotonic=observed_at_monotonic,
            ),
        )

    @staticmethod
    def _urls(collection: list[ObservedRequest]) -> list[str]:
        return [request.url for request in collection]

    def _startup_urls(
        self,
        collection: list[ObservedRequest],
        *,
        within_seconds: float,
    ) -> list[str]:
        started_at = self.startup_started_monotonic
        if started_at is None:
            return []
        deadline = started_at + within_seconds
        return [
            request.url
            for request in collection
            if request.observed_at_monotonic <= deadline
        ]


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

    def __enter__(self):
        session = super().__enter__()
        self._observation.startup_started_monotonic = monotonic()
        return session

    def _handle_github_api_route(self, route) -> None:
        url = route.request.url
        observed_at_monotonic = monotonic()
        if not self._observation.tracks_repository_url(url):
            self._continue_github_api_route(route)
            return
        if self._is_recursive_tree_url(url):
            self._observation.record_tree_url(
                url,
                observed_at_monotonic=observed_at_monotonic,
            )
        elif "/contents/" in url:
            self._observation.record_content_url(
                url,
                observed_at_monotonic=observed_at_monotonic,
            )
        self._continue_github_api_route(route)

    def _is_recursive_tree_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return (
            parsed.path.startswith(f"/repos/{self._observation.repository}/git/trees/")
            and parse_qs(parsed.query).get("recursive") == ["1"]
        )

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightStoredTokenWebAppRuntime,
)


@dataclass
class DeferredTabHydrationObservation:
    issue_path: str
    comment_paths: tuple[str, ...]
    comment_urls: list[str] = field(default_factory=list)
    requested_comment_paths: list[str] = field(default_factory=list)
    history_urls: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "issue_path": self.issue_path,
            "comment_paths": list(self.comment_paths),
            "comments": {
                "requestCount": len(self.comment_urls),
                "requestedPaths": list(self.requested_comment_paths),
                "urls": list(self.comment_urls),
            },
            "history": {
                "requestCount": len(self.history_urls),
                "urls": list(self.history_urls),
            },
        }


class DeferredTabHydrationObserverRuntime(PlaywrightStoredTokenWebAppRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        issue_path: str,
        comment_paths: list[str],
    ) -> None:
        super().__init__(repository=repository, token=token)
        self._observation = DeferredTabHydrationObservation(
            issue_path=issue_path,
            comment_paths=tuple(comment_paths),
        )

    @property
    def observation(self) -> DeferredTabHydrationObservation:
        return self._observation

    def _handle_github_api_route(self, route) -> None:
        url = route.request.url
        if self._tracks_comment_url(url):
            self._observation.comment_urls.append(url)
            matched_path = self._matched_comment_path(url)
            if (
                matched_path is not None
                and matched_path not in self._observation.requested_comment_paths
            ):
                self._observation.requested_comment_paths.append(matched_path)
        if self._tracks_history_url(url):
            self._observation.history_urls.append(url)
        self._continue_github_api_route(route)

    def _tracks_comment_url(self, url: str) -> bool:
        return self._matched_comment_path(url) is not None

    def _matched_comment_path(self, url: str) -> str | None:
        for path in self._observation.comment_paths:
            if f"/contents/{path}" in url:
                return path
        return None

    def _tracks_history_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.path != f"/repos/{self._repository}/commits":
            return False
        query = parse_qs(parsed.query)
        return query.get("path", [""])[0] == self._observation.issue_path

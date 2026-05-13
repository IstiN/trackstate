from __future__ import annotations

import json
from dataclasses import dataclass, field

from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightStoredTokenWebAppRuntime,
)


@dataclass
class CommentsArtifactOutageObservation:
    comment_paths: tuple[str, ...]
    failed_comment_path: str
    failure_message: str
    blocked_urls: list[str] = field(default_factory=list)
    allowed_urls: list[str] = field(default_factory=list)

    @classmethod
    def from_comment_paths(
        cls,
        comment_paths: list[str],
        *,
        failure_message: str,
    ) -> CommentsArtifactOutageObservation:
        if not comment_paths:
            raise ValueError("CommentsArtifactOutageObservation requires at least one comment path.")
        return cls(
            comment_paths=tuple(comment_paths),
            failed_comment_path=comment_paths[0],
            failure_message=failure_message,
        )

    def tracks_url(self, url: str) -> bool:
        return any(f"/contents/{path}" in url for path in self.comment_paths)

    def targets_failed_url(self, url: str) -> bool:
        return f"/contents/{self.failed_comment_path}" in url

    def tracked_path_for_url(self, url: str) -> str | None:
        for path in self.comment_paths:
            if f"/contents/{path}" in url:
                return path
        return None

    @property
    def blocked_was_exercised(self) -> bool:
        return len(self.blocked_urls) > 0

    @property
    def retry_refetch_was_exercised(self) -> bool:
        return len(self.allowed_urls) > 0


class CommentsArtifactOutageRuntime(PlaywrightStoredTokenWebAppRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        observation: CommentsArtifactOutageObservation,
        status_code: int = 503,
    ) -> None:
        super().__init__(repository=repository, token=token)
        self._observation = observation
        self._status_code = status_code
        self._block_comments = True

    def restore_connectivity(self) -> None:
        self._block_comments = False

    def _handle_github_api_route(self, route) -> None:
        url = route.request.url
        if not self._observation.tracks_url(url):
            self._continue_github_api_route(route)
            return
        if self._block_comments and self._observation.targets_failed_url(url):
            self._observation.blocked_urls.append(url)
            route.fulfill(
                status=self._status_code,
                content_type="application/json",
                body=json.dumps({"message": self._observation.failure_message}),
            )
            return
        self._observation.allowed_urls.append(url)
        self._continue_github_api_route(route)

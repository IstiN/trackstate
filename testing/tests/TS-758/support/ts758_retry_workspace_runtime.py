from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Route

from testing.tests.support.stored_workspace_profiles_runtime import (
    StoredWorkspaceProfilesRuntime,
)


@dataclass
class Ts758RetryWorkspaceObservation:
    repository: str
    invalid_ref: str
    requested_urls: list[str] = field(default_factory=list)
    initial_validation_urls: list[str] = field(default_factory=list)
    post_repair_validation_urls: list[str] = field(default_factory=list)

    def record(self, url: str, *, repaired: bool) -> None:
        self.requested_urls.append(url)
        target_urls = (
            self.post_repair_validation_urls if repaired else self.initial_validation_urls
        )
        target_urls.append(url)

    @property
    def initial_validation_request_count(self) -> int:
        return len(self.initial_validation_urls)

    @property
    def post_repair_validation_request_count(self) -> int:
        return len(self.post_repair_validation_urls)


class Ts758RetryWorkspaceRuntime(StoredWorkspaceProfilesRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        invalid_ref: str,
        observation: Ts758RetryWorkspaceObservation,
    ) -> None:
        super().__init__(
            repository=repository,
            token=token,
            workspace_state=workspace_state,
        )
        self._repository = repository
        self._invalid_ref = invalid_ref
        self._observation = observation
        self._repair_enabled = False

    def enable_repair(self) -> None:
        self._repair_enabled = True

    def _handle_github_api_route(self, route: Route) -> None:
        url = route.request.url
        if self._targets_invalid_workspace(url):
            self._observation.record(url, repaired=self._repair_enabled)
        super()._handle_github_api_route(route)

    def _targets_invalid_workspace(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.lower()
        query = parse_qs(parsed.query)
        repository_prefix = f"/repos/{self._repository.lower()}/"
        invalid_ref = self._invalid_ref.lower()
        return path.startswith(repository_prefix) and (
            f"/git/trees/{invalid_ref}" in path
            or invalid_ref in [value.lower() for value in query.get("ref", [])]
        )

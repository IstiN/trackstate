from __future__ import annotations

from dataclasses import dataclass, field

from playwright.sync_api import Route

from testing.tests.support.stored_workspace_profiles_runtime import (
    StoredWorkspaceProfilesRuntime,
)


@dataclass
class Ts759RetryRequestObservation:
    requested_urls: list[str] = field(default_factory=list)

    def record(self, url: str) -> None:
        self.requested_urls.append(url)

    def invalid_branch_urls(self, *, branch: str) -> tuple[str, ...]:
        branch_fragment = f"/git/trees/{branch.lower()}?recursive=1"
        return tuple(url for url in self.requested_urls if branch_fragment in url.lower())


class Ts759InvalidWorkspaceRetryRuntime(StoredWorkspaceProfilesRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        observation: Ts759RetryRequestObservation,
    ) -> None:
        super().__init__(
            repository=repository,
            token=token,
            workspace_state=workspace_state,
        )
        self._observation = observation

    def _handle_github_api_route(self, route: Route) -> None:
        self._observation.record(route.request.url)
        super()._handle_github_api_route(route)

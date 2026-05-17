from __future__ import annotations

from dataclasses import dataclass, field

from playwright.sync_api import Route

from testing.tests.support.stored_workspace_profiles_runtime import (
    StoredWorkspaceProfilesRuntime,
)


@dataclass
class Ts727RestoreRequestObservation:
    requested_urls: list[str] = field(default_factory=list)

    def record(self, url: str) -> None:
        self.requested_urls.append(url)

    def invalid_branch_urls(self, *, repository: str, branch: str) -> tuple[str, ...]:
        del repository
        branch_fragment = f"/git/trees/{branch.lower()}?recursive=1"
        return tuple(url for url in self.requested_urls if branch_fragment in url.lower())

    def default_bootstrap_urls(self, *, repository: str, ref: str) -> tuple[str, ...]:
        del repository
        expected_fragments = (
            f"/git/trees/{ref.lower()}?recursive=1",
            f"/contents/demo/project.json?ref={ref.lower()}",
        )
        return tuple(
            url
            for url in self.requested_urls
            if any(fragment in url.lower() for fragment in expected_fragments)
        )


class Ts727InvalidWorkspaceRestoreRuntime(StoredWorkspaceProfilesRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        observation: Ts727RestoreRequestObservation,
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

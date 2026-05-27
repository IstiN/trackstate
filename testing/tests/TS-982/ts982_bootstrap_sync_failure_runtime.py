from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import json
from urllib.parse import urlparse

from playwright.sync_api import Route

from testing.tests.support.stored_workspace_profiles_runtime import (
    StoredWorkspaceProfilesRuntime,
)


@dataclass(frozen=True)
class Ts982BlockedRequestObservation:
    url: str
    path: str
    attempt: int
    status_code: int


@dataclass
class Ts982BootstrapSyncFailureObservation:
    repository: str
    startup_sync_urls: list[str] = field(default_factory=list)
    all_repository_request_urls: list[str] = field(default_factory=list)
    blocked_requests: list[Ts982BlockedRequestObservation] = field(default_factory=list)

    @property
    def startup_sync_path(self) -> str:
        return f"/repos/{self.repository}/branches/main".lower()

    @property
    def blocked_was_exercised(self) -> bool:
        return len(self.blocked_requests) > 0

    def record_startup_sync_request(self, url: str, *, path: str) -> int:
        self.all_repository_request_urls.append(url)
        normalized_path = path.lower()
        if normalized_path == self.startup_sync_path:
            self.startup_sync_urls.append(url)
            return len(self.startup_sync_urls)
        return 0

    def record_blocked_request(
        self,
        *,
        url: str,
        path: str,
        attempt: int,
        status_code: int,
    ) -> None:
        self.blocked_requests.append(
            Ts982BlockedRequestObservation(
                url=url,
                path=path,
                attempt=attempt,
                status_code=status_code,
            ),
        )


class Ts982BootstrapSyncFailureRuntime(StoredWorkspaceProfilesRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        observation: Ts982BootstrapSyncFailureObservation,
        fail_status_code: int = 500,
        fail_on_startup_sync_attempt: int = 1,
    ) -> None:
        super().__init__(repository=repository, token=token, workspace_state=workspace_state)
        self._observation = observation
        self._fail_status_code = fail_status_code
        self._fail_on_startup_sync_attempt = fail_on_startup_sync_attempt
        self._request_counts: Counter[str] = Counter()

    @property
    def observation(self) -> Ts982BootstrapSyncFailureObservation:
        return self._observation

    def _handle_github_api_route(self, route: Route) -> None:
        url = route.request.url
        path = urlparse(url).path
        if self._repository.lower() not in url.lower():
            self._continue_github_api_route(route)
            return

        normalized_path = path.lower()
        self._request_counts[normalized_path] += 1
        startup_sync_attempt = self._observation.record_startup_sync_request(
            url,
            path=path,
        )
        if (
            normalized_path == self._observation.startup_sync_path
            and startup_sync_attempt == self._fail_on_startup_sync_attempt
            and not self._observation.blocked_was_exercised
        ):
            self._observation.record_blocked_request(
                url=url,
                path=path,
                attempt=startup_sync_attempt,
                status_code=self._fail_status_code,
            )
            route.fulfill(
                status=self._fail_status_code,
                content_type="application/json",
                body=json.dumps(
                    {
                        "message": "Internal Server Error",
                        "source": "TS-982 bootstrap sync failure runtime",
                    },
                ),
            )
            return
        self._continue_github_api_route(route)

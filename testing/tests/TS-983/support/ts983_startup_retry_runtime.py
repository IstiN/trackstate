from __future__ import annotations

from dataclasses import dataclass
import json
import time

from playwright.sync_api import Route

from testing.tests.support.stored_workspace_profiles_runtime import (
    StoredWorkspaceProfilesRuntime,
)


@dataclass(frozen=True)
class Ts983InterceptedRequest:
    outcome: str
    url: str
    observed_at_monotonic: float


class Ts983StartupRetryRuntime(StoredWorkspaceProfilesRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        blocked_path: str,
        workspace_token_profile_ids: tuple[str, ...] = (),
    ) -> None:
        super().__init__(
            repository=repository,
            token=token,
            workspace_state=workspace_state,
            workspace_token_profile_ids=workspace_token_profile_ids,
        )
        self._blocked_path = blocked_path
        self._allow_success = False
        self._requests: list[Ts983InterceptedRequest] = []

    def enable_retry_success(self) -> None:
        self._allow_success = True

    @property
    def blocked_requests(self) -> tuple[Ts983InterceptedRequest, ...]:
        return tuple(request for request in self._requests if request.outcome == "blocked")

    @property
    def successful_retry_requests(self) -> tuple[Ts983InterceptedRequest, ...]:
        return tuple(request for request in self._requests if request.outcome == "allowed")

    @property
    def blocked_path(self) -> str:
        return self._blocked_path

    def _handle_github_api_route(self, route: Route) -> None:
        url = route.request.url
        if f"/contents/{self._blocked_path}" in url:
            outcome = "allowed" if self._allow_success else "blocked"
            self._requests.append(
                Ts983InterceptedRequest(
                    outcome=outcome,
                    url=url,
                    observed_at_monotonic=time.monotonic(),
                ),
            )
            if outcome == "blocked":
                route.fulfill(
                    status=403,
                    content_type="application/json",
                    body=json.dumps(
                        {
                            "message": (
                                "API rate limit exceeded for TS-983 synthetic startup "
                                "retry probe"
                            ),
                            "documentation_url": (
                                "https://docs.github.com/rest/overview/resources-in-the-rest-api"
                                "#rate-limiting"
                            ),
                        },
                    ),
                    headers={
                        "x-ratelimit-remaining": "0",
                        "retry-after": "60",
                    },
                )
                return
        self._continue_github_api_route(route)

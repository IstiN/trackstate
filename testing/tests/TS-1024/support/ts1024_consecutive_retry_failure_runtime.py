from __future__ import annotations

from dataclasses import dataclass
import json
import time

from playwright.sync_api import Route

from testing.tests.support.stored_workspace_profiles_runtime import (
    StoredWorkspaceProfilesRuntime,
)


@dataclass(frozen=True)
class Ts1024InterceptedRequest:
    phase: str
    url: str
    status_code: int
    observed_at_monotonic: float


class Ts1024ConsecutiveRetryFailureRuntime(StoredWorkspaceProfilesRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        blocked_path: str,
        initial_failure_status_code: int = 403,
        retry_failure_status_code: int = 500,
    ) -> None:
        super().__init__(
            repository=repository,
            token=token,
            workspace_state=workspace_state,
        )
        self._blocked_path = blocked_path
        self._initial_failure_status_code = initial_failure_status_code
        self._retry_failure_status_code = retry_failure_status_code
        self._requests: list[Ts1024InterceptedRequest] = []

    @property
    def blocked_path(self) -> str:
        return self._blocked_path

    @property
    def failure_status_code(self) -> int:
        return self._retry_failure_status_code

    @property
    def requests(self) -> tuple[Ts1024InterceptedRequest, ...]:
        return tuple(self._requests)

    @property
    def initial_failed_requests(self) -> tuple[Ts1024InterceptedRequest, ...]:
        return tuple(request for request in self._requests if request.phase == "initial")

    @property
    def retry_failed_requests(self) -> tuple[Ts1024InterceptedRequest, ...]:
        return tuple(request for request in self._requests if request.phase == "retry")

    def _handle_github_api_route(self, route: Route) -> None:
        url = route.request.url
        if f"/contents/{self._blocked_path}" in url:
            phase = "initial" if not self._requests else "retry"
            status_code = (
                self._initial_failure_status_code
                if phase == "initial"
                else self._retry_failure_status_code
            )
            self._requests.append(
                Ts1024InterceptedRequest(
                    phase=phase,
                    url=url,
                    status_code=status_code,
                    observed_at_monotonic=time.monotonic(),
                ),
            )
            if phase == "initial":
                response_body = {
                    "message": "API rate limit exceeded for TS-1024 startup recovery probe",
                    "documentation_url": (
                        "https://docs.github.com/rest/overview/resources-in-the-rest-api"
                        "#rate-limiting"
                    ),
                    "source": "TS-1024 consecutive retry failure runtime",
                    "phase": phase,
                }
                response_headers = {
                    "x-ratelimit-remaining": "0",
                    "retry-after": "60",
                }
            else:
                response_body = {
                    "message": "Internal Server Error",
                    "source": "TS-1024 consecutive retry failure runtime",
                    "phase": phase,
                }
                response_headers = None
            route.fulfill(
                status=status_code,
                content_type="application/json",
                body=json.dumps(response_body),
                headers=response_headers,
            )
            return
        self._continue_github_api_route(route)

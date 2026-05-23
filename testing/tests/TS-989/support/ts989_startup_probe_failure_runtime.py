from __future__ import annotations

import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import urlparse

from playwright.sync_api import Route

from testing.tests.support.stored_workspace_profiles_runtime import (
    StoredWorkspaceProfilesRuntime,
)


@dataclass(frozen=True)
class Ts989StartupProbeFailureRequest:
    url: str
    path: str
    attempt: int
    error_code: str
    observed_at_monotonic: float


@dataclass
class Ts989StartupProbeFailureObservation:
    github_request_urls: list[str] = field(default_factory=list)
    failed_request_urls: list[str] = field(default_factory=list)
    failed_requests: list[Ts989StartupProbeFailureRequest] = field(default_factory=list)

    @property
    def failure_exercised(self) -> bool:
        return len(self.failed_requests) > 0


class Ts989StartupProbeFailureRuntime(StoredWorkspaceProfilesRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        observation: Ts989StartupProbeFailureObservation,
        failure_paths: tuple[str, ...] = ("/user",),
        fail_on_attempt: int = 1,
        abort_error_code: str = "failed",
        workspace_token_profile_ids: tuple[str, ...] = (),
    ) -> None:
        super().__init__(
            repository=repository,
            token=token,
            workspace_state=workspace_state,
            workspace_token_profile_ids=workspace_token_profile_ids,
        )
        self._observation = observation
        self._failure_paths = tuple(failure_paths)
        self._fail_on_attempt = fail_on_attempt
        self._abort_error_code = abort_error_code
        self._request_counts: Counter[str] = Counter()
        self._probe_started = threading.Event()
        self._probe_released = threading.Event()
        self._probe_lock = threading.Lock()
        self._pending_probe_requests = 0
        self.auth_probe_started_at_monotonic: float | None = None
        self.auth_probe_released_at_monotonic: float | None = None

    def wait_for_auth_probe_start(self, *, timeout_seconds: float) -> bool:
        return self._probe_started.wait(timeout_seconds)

    def wait_for_auth_probe_release(self, *, timeout_seconds: float) -> bool:
        return self._probe_released.wait(timeout_seconds)

    @property
    def auth_probe_pending(self) -> bool:
        with self._probe_lock:
            return self._pending_probe_requests > 0

    @property
    def github_request_urls(self) -> list[str]:
        return self._observation.github_request_urls

    @property
    def delayed_request_urls(self) -> list[str]:
        return self._observation.failed_request_urls

    def _handle_github_api_route(self, route: Route) -> None:
        request_url = route.request.url
        self._observation.github_request_urls.append(request_url)
        if not self._matches_failure_path(request_url):
            self._continue_github_api_route(route)
            return

        path = urlparse(request_url).path.rstrip("/") or "/"
        self._request_counts[path] += 1
        attempt = self._request_counts[path]
        with self._probe_lock:
            self._pending_probe_requests += 1
            if self.auth_probe_started_at_monotonic is None:
                self.auth_probe_started_at_monotonic = time.monotonic()
            self._probe_started.set()

        try:
            if attempt == self._fail_on_attempt and not self._observation.failure_exercised:
                observed_at = time.monotonic()
                self._observation.failed_request_urls.append(request_url)
                self._observation.failed_requests.append(
                    Ts989StartupProbeFailureRequest(
                        url=request_url,
                        path=path,
                        attempt=attempt,
                        error_code=self._abort_error_code,
                        observed_at_monotonic=observed_at,
                    ),
                )
                route.abort(self._abort_error_code)
                return
            self._continue_github_api_route(route)
        finally:
            with self._probe_lock:
                self._pending_probe_requests -= 1
                if self._pending_probe_requests == 0:
                    self.auth_probe_released_at_monotonic = time.monotonic()
                    self._probe_released.set()

    def _matches_failure_path(self, request_url: str) -> bool:
        path = urlparse(request_url).path.rstrip("/") or "/"
        return any(
            path == failure_path or path.endswith(failure_path)
            for failure_path in self._failure_paths
        )

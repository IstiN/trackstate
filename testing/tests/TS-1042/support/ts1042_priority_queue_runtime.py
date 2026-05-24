from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

from playwright.sync_api import Route

from testing.tests.support.stored_workspace_profiles_runtime import (
    StoredWorkspaceProfilesRuntime,
)


@dataclass
class Ts1042StartupPriorityObservation:
    repository: str
    github_request_urls: list[str] = field(default_factory=list)
    delayed_request_urls: list[str] = field(default_factory=list)
    delayed_auth_request_urls: list[str] = field(default_factory=list)
    delayed_secondary_request_urls: list[str] = field(default_factory=list)
    auth_probe_started_at_monotonic: float | None = None
    auth_probe_released_at_monotonic: float | None = None
    secondary_probe_started_at_monotonic: float | None = None
    secondary_probe_released_at_monotonic: float | None = None


class Ts1042StartupPriorityQueueRuntime(StoredWorkspaceProfilesRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        observation: Ts1042StartupPriorityObservation,
        auth_delay_seconds: float,
        secondary_delay_seconds: float,
        secondary_paths: tuple[str, ...],
        workspace_token_profile_ids: tuple[str, ...] = (),
    ) -> None:
        super().__init__(
            repository=repository,
            token=token,
            workspace_state=workspace_state,
            workspace_token_profile_ids=workspace_token_profile_ids,
        )
        self._observation = observation
        self._auth_delay_seconds = float(auth_delay_seconds)
        self._secondary_delay_seconds = float(secondary_delay_seconds)
        self._secondary_paths = tuple(secondary_paths)
        self._delay_lock = threading.Lock()
        self._pending_auth_requests = 0
        self._pending_secondary_requests = 0

    @property
    def observation(self) -> Ts1042StartupPriorityObservation:
        return self._observation

    @property
    def auth_probe_pending(self) -> bool:
        with self._delay_lock:
            return self._pending_auth_requests > 0

    @property
    def secondary_probe_pending(self) -> bool:
        with self._delay_lock:
            return self._pending_secondary_requests > 0

    def _handle_github_api_route(self, route: Route) -> None:
        request_url = route.request.url
        self._observation.github_request_urls.append(request_url)
        request_path = urlparse(request_url).path.rstrip("/") or "/"
        if request_path == "/user":
            self._delay_auth_route(route, request_url)
            return
        if self._matches_secondary_path(request_url):
            self._delay_secondary_route(route, request_url)
            return
        self._continue_github_api_route(route)

    def _delay_auth_route(self, route: Route, request_url: str) -> None:
        self._observation.delayed_request_urls.append(request_url)
        self._observation.delayed_auth_request_urls.append(request_url)
        with self._delay_lock:
            self._pending_auth_requests += 1
            if self._observation.auth_probe_started_at_monotonic is None:
                self._observation.auth_probe_started_at_monotonic = time.monotonic()
        try:
            time.sleep(self._auth_delay_seconds)
        finally:
            with self._delay_lock:
                self._pending_auth_requests -= 1
                if self._pending_auth_requests == 0:
                    self._observation.auth_probe_released_at_monotonic = time.monotonic()
        self._continue_github_api_route(route)

    def _delay_secondary_route(self, route: Route, request_url: str) -> None:
        self._observation.delayed_request_urls.append(request_url)
        self._observation.delayed_secondary_request_urls.append(request_url)
        with self._delay_lock:
            self._pending_secondary_requests += 1
            if self._observation.secondary_probe_started_at_monotonic is None:
                self._observation.secondary_probe_started_at_monotonic = time.monotonic()
        try:
            time.sleep(self._secondary_delay_seconds)
        finally:
            with self._delay_lock:
                self._pending_secondary_requests -= 1
                if self._pending_secondary_requests == 0:
                    self._observation.secondary_probe_released_at_monotonic = (
                        time.monotonic()
                    )
        self._continue_github_api_route(route)

    def _matches_secondary_path(self, request_url: str) -> bool:
        return any(secondary_path in request_url for secondary_path in self._secondary_paths)

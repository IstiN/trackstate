from __future__ import annotations

import threading
import time
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Route

from testing.tests.support.stored_workspace_profiles_runtime import (
    StoredWorkspaceProfilesRuntime,
)


class DelayedAuthWorkspaceProfilesRuntime(StoredWorkspaceProfilesRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        auth_delay_seconds: float,
        delayed_paths: tuple[str, ...] = ("/user",),
        workspace_token_profile_ids: tuple[str, ...] = (),
    ) -> None:
        super().__init__(
            repository=repository,
            token=token,
            workspace_state=workspace_state,
            workspace_token_profile_ids=workspace_token_profile_ids,
        )
        self._auth_delay_seconds = float(auth_delay_seconds)
        self._delayed_paths = delayed_paths
        self._auth_request_started = threading.Event()
        self._auth_request_released = threading.Event()
        self._first_auth_request_released = threading.Event()
        self._delay_lock = threading.Lock()
        self._pending_delayed_requests = 0
        self._delayed_request_sequence = 0
        self.auth_probe_started_at_monotonic: float | None = None
        self.auth_probe_released_at_monotonic: float | None = None
        self.first_auth_probe_released_at_monotonic: float | None = None
        self.github_request_urls: list[str] = []
        self.delayed_request_urls: list[str] = []
        self.delayed_request_timings: list[dict[str, Any]] = []

    def wait_for_auth_probe_start(self, *, timeout_seconds: float) -> bool:
        return self._wait_for_event(
            self._auth_request_started,
            timeout_seconds=timeout_seconds,
        )

    def wait_for_auth_probe_release(self, *, timeout_seconds: float) -> bool:
        return self._wait_for_event(
            self._auth_request_released,
            timeout_seconds=timeout_seconds,
        )

    def wait_for_first_auth_probe_release(self, *, timeout_seconds: float) -> bool:
        return self._wait_for_event(
            self._first_auth_request_released,
            timeout_seconds=timeout_seconds,
        )

    @property
    def auth_probe_pending(self) -> bool:
        with self._delay_lock:
            return self._pending_delayed_requests > 0

    def _handle_github_api_route(self, route: Route) -> None:
        request_url = route.request.url
        self.github_request_urls.append(request_url)
        if self._matches_delayed_path(request_url):
            self.delayed_request_urls.append(request_url)
            request_started_at_monotonic = time.monotonic()
            with self._delay_lock:
                self._pending_delayed_requests += 1
                self._delayed_request_sequence += 1
                request_index = self._delayed_request_sequence
                request_timing: dict[str, Any] = {
                    "index": request_index,
                    "url": request_url,
                    "started_at_monotonic": request_started_at_monotonic,
                    "released_at_monotonic": None,
                }
                self.delayed_request_timings.append(request_timing)
                if self.auth_probe_started_at_monotonic is None:
                    self.auth_probe_started_at_monotonic = request_started_at_monotonic
                self._auth_request_started.set()
            try:
                time.sleep(self._auth_delay_seconds)
            finally:
                request_released_at_monotonic = time.monotonic()
                with self._delay_lock:
                    request_timing["released_at_monotonic"] = request_released_at_monotonic
                    if request_index == 1:
                        self.first_auth_probe_released_at_monotonic = (
                            request_released_at_monotonic
                        )
                        self._first_auth_request_released.set()
                    self._pending_delayed_requests -= 1
                    if self._pending_delayed_requests == 0:
                        self.auth_probe_released_at_monotonic = (
                            request_released_at_monotonic
                        )
                        self._auth_request_released.set()
        self._continue_github_api_route(route)

    def _matches_delayed_path(self, request_url: str) -> bool:
        path = urlparse(request_url).path.rstrip("/") or "/"
        return any(
            path == delayed_path or path.endswith(delayed_path)
            for delayed_path in self._delayed_paths
        )

    def _wait_for_event(
        self,
        event: threading.Event,
        *,
        timeout_seconds: float,
        poll_interval_ms: int = 100,
    ) -> bool:
        if event.is_set():
            return True
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            page = self._page
            if page is not None:
                page.wait_for_timeout(poll_interval_ms)
            else:
                time.sleep(poll_interval_ms / 1000)
            if event.is_set():
                return True
        return event.is_set()

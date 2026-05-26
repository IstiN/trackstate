from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from testing.tests.support.stored_workspace_profiles_runtime import (
    StoredWorkspaceProfilesRuntime,
)

if TYPE_CHECKING:
    from playwright.sync_api import ConsoleMessage
    from playwright.sync_api import Route
else:
    ConsoleMessage = Any
    Route = Any


class DelayedAuthWorkspaceProfilesRuntime(StoredWorkspaceProfilesRuntime):
    _START_CONSOLE_PREFIX = "__trackstateDelayedAuthStart__ "
    _RELEASE_CONSOLE_PREFIX = "__trackstateDelayedAuthRelease__ "

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

    def __enter__(self):
        session = super().__enter__()
        if self._context is None or self._page is None:
            raise RuntimeError(
                "DelayedAuthWorkspaceProfilesRuntime expected a browser context and page.",
            )
        script = _build_delayed_auth_fetch_script(
            auth_delay_seconds=self._auth_delay_seconds,
            delayed_paths=self._delayed_paths,
            start_prefix=self._START_CONSOLE_PREFIX,
            release_prefix=self._RELEASE_CONSOLE_PREFIX,
        )
        self._context.add_init_script(script=script)
        self._page.add_init_script(script=script)
        self._page.on("console", self._handle_console_message)
        return session

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
        self._continue_github_api_route(route)

    def _handle_console_message(self, message: ConsoleMessage) -> None:
        text = message.text or ""
        if text.startswith(self._START_CONSOLE_PREFIX):
            self._record_delayed_request_start(text[len(self._START_CONSOLE_PREFIX) :].strip())
            return
        if text.startswith(self._RELEASE_CONSOLE_PREFIX):
            self._record_delayed_request_release(
                text[len(self._RELEASE_CONSOLE_PREFIX) :].strip(),
            )

    def _record_delayed_request_start(self, request_url: str) -> None:
        if not request_url:
            return
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
            self.delayed_request_urls.append(request_url)
            self.delayed_request_timings.append(request_timing)
            if self.auth_probe_started_at_monotonic is None:
                self.auth_probe_started_at_monotonic = request_started_at_monotonic
            self._auth_request_started.set()

    def _record_delayed_request_release(self, request_url: str) -> None:
        if not request_url:
            return
        request_released_at_monotonic = time.monotonic()
        with self._delay_lock:
            request_timing = next(
                (
                    timing
                    for timing in reversed(self.delayed_request_timings)
                    if timing.get("url") == request_url
                    and timing.get("released_at_monotonic") is None
                ),
                None,
            )
            if request_timing is None:
                return
            request_timing["released_at_monotonic"] = request_released_at_monotonic
            if request_timing["index"] == 1:
                self.first_auth_probe_released_at_monotonic = (
                    request_released_at_monotonic
                )
                self._first_auth_request_released.set()
            self._pending_delayed_requests = max(0, self._pending_delayed_requests - 1)
            if self._pending_delayed_requests == 0:
                self.auth_probe_released_at_monotonic = request_released_at_monotonic
                self._auth_request_released.set()

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


def _build_delayed_auth_fetch_script(
    *,
    auth_delay_seconds: float,
    delayed_paths: tuple[str, ...],
    start_prefix: str,
    release_prefix: str,
) -> str:
    delay_ms = max(0, round(auth_delay_seconds * 1000))
    return f"""
(() => {{
  if (window.__trackstateDelayedAuthFetchPatched) {{
    return;
  }}
  window.__trackstateDelayedAuthFetchPatched = true;
  const delayedPaths = {list(delayed_paths)!r};
  const delayMs = {delay_ms};
  const startPrefix = {start_prefix!r};
  const releasePrefix = {release_prefix!r};
  const originalFetch = window.fetch.bind(window);
  const normalizePath = (value) => {{
    try {{
      const path = new URL(value, window.location.href).pathname.replace(/\\/+$/, '');
      return path || '/';
    }} catch (_error) {{
      return '';
    }}
  }};
  const shouldDelay = (value) => {{
    const path = normalizePath(value);
    return delayedPaths.some((delayedPath) => path === delayedPath || path.endsWith(delayedPath));
  }};
  const requestUrl = (input) => {{
    if (typeof input === 'string') {{
      return input;
    }}
    if (input && typeof input.url === 'string') {{
      return input.url;
    }}
    return String(input ?? '');
  }};
  window.fetch = async (input, init) => {{
    const url = requestUrl(input);
    if (!shouldDelay(url)) {{
      return originalFetch(input, init);
    }}
    console.info(`${{startPrefix}}${{url}}`);
    await new Promise((resolve) => window.setTimeout(resolve, delayMs));
    console.info(`${{releasePrefix}}${{url}}`);
    return originalFetch(input, init);
  }};
}})();
"""

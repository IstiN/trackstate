from __future__ import annotations

import json
import threading
import time
from typing import Any

from playwright.sync_api import Route
from testing.frameworks.python.playwright_web_app_session import PlaywrightWebAppSession

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
        self._delay_lock = threading.Lock()
        self._pending_delayed_requests = 0
        self.auth_probe_started_at_monotonic: float | None = None
        self.auth_probe_released_at_monotonic: float | None = None
        self.github_request_urls: list[str] = []
        self.delayed_request_urls: list[str] = []

    def __enter__(self) -> PlaywrightWebAppSession:
        session = super().__enter__()
        script = _build_delayed_fetch_script(
            delayed_paths=self._delayed_paths,
            delay_ms=int(self._auth_delay_seconds * 1000),
        )
        if self._context is None or self._page is None:
            raise RuntimeError(
                "DelayedAuthWorkspaceProfilesRuntime expected a browser context and page.",
            )
        self._context.add_init_script(script=script)
        self._page.add_init_script(script=script)
        return session

    def wait_for_auth_probe_start(self, *, timeout_seconds: float) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            state = self._read_delay_state()
            self._sync_delay_state(state)
            if state["started_urls"]:
                return True
            time.sleep(0.1)
        state = self._read_delay_state()
        self._sync_delay_state(state)
        return bool(state["started_urls"])

    def wait_for_auth_probe_release(self, *, timeout_seconds: float) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            state = self._read_delay_state()
            self._sync_delay_state(state)
            if state["started_urls"] and state["active_count"] == 0:
                return True
            time.sleep(0.1)
        state = self._read_delay_state()
        self._sync_delay_state(state)
        return bool(state["started_urls"]) and state["active_count"] == 0

    @property
    def auth_probe_pending(self) -> bool:
        state = self._read_delay_state()
        self._sync_delay_state(state)
        return state["active_count"] > 0

    def _handle_github_api_route(self, route: Route) -> None:
        request_url = route.request.url
        self.github_request_urls.append(request_url)
        self._continue_github_api_route(route)

    def _read_delay_state(self) -> dict[str, Any]:
        if self._page is None:
            return {
                "active_count": 0,
                "started_urls": [],
                "completed_urls": [],
            }
        payload = self._page.evaluate(
            """
            () => {
              const state = window.__delayedAuthWorkspaceProfilesState;
              if (!state) {
                return null;
              }
              return {
                activeCount: state.activeCount,
                startedUrls: [...state.startedUrls],
                completedUrls: [...state.completedUrls],
              };
            }
            """,
        )
        if not isinstance(payload, dict):
            return {
                "active_count": 0,
                "started_urls": [],
                "completed_urls": [],
            }
        return {
            "active_count": int(payload.get("activeCount", 0) or 0),
            "started_urls": [
                str(url)
                for url in payload.get("startedUrls", [])
                if isinstance(url, str)
            ],
            "completed_urls": [
                str(url)
                for url in payload.get("completedUrls", [])
                if isinstance(url, str)
            ],
        }

    def _sync_delay_state(self, state: dict[str, Any]) -> None:
        started_urls = state["started_urls"]
        completed_urls = state["completed_urls"]
        with self._delay_lock:
            self._pending_delayed_requests = int(state["active_count"])
            self.delayed_request_urls = list(started_urls)
            if started_urls and self.auth_probe_started_at_monotonic is None:
                self.auth_probe_started_at_monotonic = time.monotonic()
                self._auth_request_started.set()
            if (
                completed_urls
                and state["active_count"] == 0
                and self.auth_probe_released_at_monotonic is None
            ):
                self.auth_probe_released_at_monotonic = time.monotonic()
                self._auth_request_released.set()


def _build_delayed_fetch_script(
    *,
    delayed_paths: tuple[str, ...],
    delay_ms: int,
) -> str:
    return (
        "(() => {"
        f"const delayedPaths = {json.dumps(list(delayed_paths))};"
        f"const delayMs = {json.dumps(delay_ms)};"
        "const state = { activeCount: 0, startedUrls: [], completedUrls: [] };"
        "window.__delayedAuthWorkspaceProfilesState = state;"
        "const normalizePath = (value) => {"
        "  try { return new URL(value, window.location.href).pathname.replace(/\\/$/, '') || '/'; }"
        "  catch (_) { return ''; }"
        "};"
        "const shouldDelay = (value) => delayedPaths.some((path) => {"
        "  const normalized = normalizePath(value);"
        "  return normalized === path || normalized.endsWith(path);"
        "});"
        "const originalFetch = window.fetch.bind(window);"
        "window.fetch = async (input, init) => {"
        "  const requestUrl = typeof input === 'string'"
        "    ? input"
        "    : (input && typeof input === 'object' && 'url' in input ? input.url : '');"
        "  if (!shouldDelay(requestUrl)) {"
        "    return originalFetch(input, init);"
        "  }"
        "  state.startedUrls.push(requestUrl);"
        "  state.activeCount += 1;"
        "  try {"
        "    await new Promise((resolve) => setTimeout(resolve, delayMs));"
        "    return await originalFetch(input, init);"
        "  } finally {"
        "    state.activeCount -= 1;"
        "    state.completedUrls.push(requestUrl);"
        "  }"
        "};"
        "})();"
    )

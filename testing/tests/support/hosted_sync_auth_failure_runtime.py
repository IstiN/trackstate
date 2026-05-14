from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

from playwright.sync_api import Route

from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightStoredTokenWebAppRuntime,
)


@dataclass(frozen=True)
class HostedSyncAuthFailureRequest:
    url: str
    observed_at_monotonic: float
    since_revocation_seconds: float


@dataclass
class HostedSyncAuthFailureObservation:
    repository: str
    revoked_at_monotonic: float | None = None
    failed_sync_requests: list[HostedSyncAuthFailureRequest] = field(default_factory=list)
    post_revocation_requests: list[HostedSyncAuthFailureRequest] = field(default_factory=list)
    post_revocation_request_urls: list[str] = field(default_factory=list)

    def mark_revoked(self) -> float:
        if self.revoked_at_monotonic is None:
            self.revoked_at_monotonic = time.monotonic()
        return self.revoked_at_monotonic

    def record_failed_sync_request(self, url: str) -> HostedSyncAuthFailureRequest:
        observed_at = time.monotonic()
        revoked_at = self.mark_revoked()
        observation = HostedSyncAuthFailureRequest(
            url=url,
            observed_at_monotonic=observed_at,
            since_revocation_seconds=observed_at - revoked_at,
        )
        self.failed_sync_requests.append(observation)
        return observation

    def record_post_revocation_request(self, url: str) -> HostedSyncAuthFailureRequest:
        observed_at = time.monotonic()
        revoked_at = self.mark_revoked()
        observation = HostedSyncAuthFailureRequest(
            url=url,
            observed_at_monotonic=observed_at,
            since_revocation_seconds=observed_at - revoked_at,
        )
        self.post_revocation_requests.append(observation)
        self.post_revocation_request_urls.append(url)
        return observation


class HostedSyncAuthFailureRuntime(PlaywrightStoredTokenWebAppRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        observation: HostedSyncAuthFailureObservation,
        workspace_state: dict[str, object],
    ) -> None:
        super().__init__(repository=repository, token=token)
        self._observation = observation
        self._revoked = False
        self._repository_path = f"/repos/{repository}"
        self._workspace_state = workspace_state

    def __enter__(self):
        session = super().__enter__()
        if self._context is None:
            raise RuntimeError(
                "HostedSyncAuthFailureRuntime expected a browser context.",
            )
        serialized_state = json.dumps(self._workspace_state)
        self._context.add_init_script(
            script=(
                "(() => {"
                f"const state = {json.dumps(serialized_state)};"
                "for (const key of ["
                "  'trackstate.workspaceProfiles.state',"
                "  'flutter.trackstate.workspaceProfiles.state',"
                "]) {"
                "  window.localStorage.setItem(key, state);"
                "}"
                "})();"
            ),
        )
        return session

    def revoke_pat(self) -> None:
        self._revoked = True
        self._observation.mark_revoked()

    def _handle_github_api_route(self, route: Route) -> None:
        url = route.request.url
        if self._revoked:
            self._observation.record_post_revocation_request(url)
        if self._revoked and self._is_repository_scoped_request(url):
            self._observation.record_failed_sync_request(url)
            route.fulfill(
                status=401,
                content_type="application/json",
                body=json.dumps(
                    {
                        "message": "Bad credentials",
                        "documentation_url": "https://docs.github.com/rest",
                    },
                ),
                headers={"www-authenticate": 'Bearer realm="GitHub"'},
            )
            return
        self._continue_github_api_route(route)

    def _is_repository_scoped_request(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/").lower()
        repository_path = self._repository_path.lower()
        return path == repository_path or path.startswith(f"{repository_path}/")

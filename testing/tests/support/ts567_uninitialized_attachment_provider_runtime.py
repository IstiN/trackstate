from __future__ import annotations

import json
from dataclasses import dataclass, field
from urllib.parse import urlparse

from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightStoredTokenWebAppRuntime,
)


@dataclass
class Ts567UninitializedAttachmentProviderObservation:
    repository: str
    permission_fault_enabled: bool = False
    intercepted_repo_urls: list[str] = field(default_factory=list)
    observed_permissions: list[dict[str, object]] = field(default_factory=list)
    blocked_mutation_urls: list[str] = field(default_factory=list)

    @property
    def repo_endpoint(self) -> str:
        return f"/repos/{self.repository}"

    def enable_permission_fault(self) -> None:
        self.permission_fault_enabled = True


class Ts567UninitializedAttachmentProviderRuntime(PlaywrightStoredTokenWebAppRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        observation: Ts567UninitializedAttachmentProviderObservation,
    ) -> None:
        super().__init__(repository=repository, token=token)
        self._observation = observation

    def _handle_github_api_route(self, route) -> None:
        request = route.request
        parsed = urlparse(request.url)

        if self._should_block_mutation(request.method, parsed.path):
            self._observation.blocked_mutation_urls.append(request.url)
            route.fulfill(
                status=409,
                content_type="application/json",
                body=json.dumps(
                    {
                        "message": (
                            "TS-567 synthetic permission fault blocked a live "
                            "repository mutation after the upload guard was triggered."
                        ),
                    },
                ),
            )
            return

        if (
            self._observation.permission_fault_enabled
            and request.method.upper() == "GET"
            and parsed.path == self._observation.repo_endpoint
        ):
            fetched = route.fetch(headers=self._authorized_github_headers(request.headers))
            payload = fetched.json()
            if not isinstance(payload, dict):
                route.fulfill(status=fetched.status, body=fetched.text())
                return

            original_permissions = payload.get("permissions")
            patched_payload = {
                key: value for key, value in payload.items() if key != "permissions"
            }
            self._observation.intercepted_repo_urls.append(request.url)
            self._observation.observed_permissions.append(
                {
                    "original": (
                        dict(original_permissions)
                        if isinstance(original_permissions, dict)
                        else {}
                    ),
                    "patched": "removed",
                },
            )
            route.fulfill(
                status=fetched.status,
                headers={
                    key: value
                    for key, value in fetched.headers.items()
                    if key.lower() != "content-length"
                },
                content_type="application/json",
                body=json.dumps(patched_payload),
            )
            return

        self._continue_github_api_route(route)

    def _should_block_mutation(self, method: str, path: str) -> bool:
        if not self._observation.permission_fault_enabled:
            return False
        if method.upper() in {"GET", "HEAD", "OPTIONS"}:
            return False
        return path.startswith(f"/repos/{self._repository}/")

from __future__ import annotations

from dataclasses import dataclass, field
import json
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from playwright.sync_api import Route

from testing.tests.support.stored_workspace_profiles_runtime import (
    StoredWorkspaceProfilesRuntime,
)


@dataclass
class Ts758RetryWorkspaceObservation:
    repository: str
    invalid_ref: str
    repaired_ref: str
    requested_urls: list[str] = field(default_factory=list)
    blocked_urls: list[str] = field(default_factory=list)
    replayed_urls: list[str] = field(default_factory=list)

    def record(self, url: str) -> None:
        self.requested_urls.append(url)

    @property
    def blocked_request_count(self) -> int:
        return len(self.blocked_urls)

    @property
    def replayed_request_count(self) -> int:
        return len(self.replayed_urls)


class Ts758RetryWorkspaceRuntime(StoredWorkspaceProfilesRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        invalid_ref: str,
        repaired_ref: str,
        observation: Ts758RetryWorkspaceObservation,
    ) -> None:
        super().__init__(
            repository=repository,
            token=token,
            workspace_state=workspace_state,
        )
        self._repository = repository
        self._invalid_ref = invalid_ref
        self._repaired_ref = repaired_ref
        self._observation = observation
        self._repair_enabled = False

    def enable_repair(self) -> None:
        self._repair_enabled = True

    def _handle_github_api_route(self, route: Route) -> None:
        url = route.request.url
        self._observation.record(url)
        if not self._targets_invalid_workspace(url):
            super()._handle_github_api_route(route)
            return

        if not self._repair_enabled:
            self._observation.blocked_urls.append(url)
            route.fulfill(
                status=404,
                content_type="application/json",
                body=json.dumps({"message": "Not Found"}),
            )
            return

        self._observation.replayed_urls.append(url)
        rewritten_url = self._rewrite_url(url)
        fetched = route.fetch(
            url=rewritten_url,
            headers=self._authorized_github_headers(route.request.headers),
        )
        route.fulfill(
            status=fetched.status,
            headers={
                key: value
                for key, value in fetched.headers.items()
                if key.lower() != "content-length"
            },
            body=fetched.text(),
        )

    def _targets_invalid_workspace(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.lower()
        query = parse_qs(parsed.query)
        repository_prefix = f"/repos/{self._repository.lower()}/"
        invalid_ref = self._invalid_ref.lower()
        return path.startswith(repository_prefix) and (
            f"/git/trees/{invalid_ref}" in path
            or invalid_ref in [value.lower() for value in query.get("ref", [])]
        )

    def _rewrite_url(self, url: str) -> str:
        parsed = urlparse(url)
        invalid_ref = self._invalid_ref
        repaired_ref = self._repaired_ref
        path = parsed.path.replace(f"/git/trees/{invalid_ref}", f"/git/trees/{repaired_ref}")
        query = parse_qs(parsed.query)
        if "ref" in query:
            query["ref"] = [
                repaired_ref if value == invalid_ref else value
                for value in query["ref"]
            ]
        return urlunparse(
            parsed._replace(
                path=path,
                query=urlencode(query, doseq=True),
            )
        )

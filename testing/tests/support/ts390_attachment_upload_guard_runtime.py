from __future__ import annotations

import json
from dataclasses import dataclass, field
from urllib.parse import urlparse

from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightStoredTokenWebAppRuntime,
)


@dataclass
class Ts390AttachmentUploadAttemptObservation:
    issue_attachments_directory: str
    attempted_upload_urls: list[str] = field(default_factory=list)

    @property
    def upload_was_attempted(self) -> bool:
        return bool(self.attempted_upload_urls)


class Ts390AttachmentUploadGuardRuntime(PlaywrightStoredTokenWebAppRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        observation: Ts390AttachmentUploadAttemptObservation,
    ) -> None:
        super().__init__(repository=repository, token=token)
        self._observation = observation

    def _handle_github_api_route(self, route) -> None:
        url = route.request.url
        if self._is_issue_attachment_write(route.request.method, url):
            self._observation.attempted_upload_urls.append(url)
            route.fulfill(
                status=409,
                content_type="application/json",
                body=json.dumps(
                    {
                        "message": (
                            "TS-390 synthetic upload guard blocked a live attachment "
                            "upload mutation."
                        ),
                    },
                ),
            )
            return
        self._continue_github_api_route(route)

    def _is_issue_attachment_write(self, method: str, url: str) -> bool:
        if method.upper() != "PUT":
            return False
        request_path = urlparse(url).path
        issue_attachments_prefix = (
            f"/repos/{self._repository}/contents/"
            f"{self._observation.issue_attachments_directory.rstrip('/')}/"
        )
        return request_path.startswith(issue_attachments_prefix)

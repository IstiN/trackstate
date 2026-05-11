from __future__ import annotations

import json
from dataclasses import dataclass, field
from urllib.parse import quote

from testing.frameworks.python.playwright_web_app_session import (
    PlaywrightStoredTokenWebAppRuntime,
)


@dataclass
class AttachmentMetadataRestrictionObservation:
    attachment_path: str
    intercepted_urls: list[str] = field(default_factory=list)

    @property
    def was_exercised(self) -> bool:
        return len(self.intercepted_urls) > 0


class AttachmentMetadataRestrictedRuntime(PlaywrightStoredTokenWebAppRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        observation: AttachmentMetadataRestrictionObservation,
    ) -> None:
        super().__init__(repository=repository, token=token)
        self._observation = observation
        self._encoded_attachment_path = quote(observation.attachment_path, safe="")

    def _handle_github_api_route(self, route) -> None:
        url = route.request.url
        if "/commits?" in url and f"path={self._encoded_attachment_path}" in url:
            self._observation.intercepted_urls.append(url)
            route.fulfill(
                status=403,
                content_type="application/json",
                body=json.dumps(
                    {
                        "message": (
                            "TS-329 synthetic restriction: attachment metadata access denied"
                        ),
                    },
                ),
            )
            return
        self._continue_github_api_route(route)

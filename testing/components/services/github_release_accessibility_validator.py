from __future__ import annotations

from contextlib import AbstractContextManager
import re

from testing.components.pages.github_release_page import GitHubReleasePage
from testing.core.config.github_release_accessibility_config import (
    GitHubReleaseAccessibilityConfig,
)
from testing.core.interfaces.github_release_accessibility_probe import (
    GitHubReleaseAccessibilityObservation,
)
from testing.core.interfaces.json_array_http_reader import (
    JsonArrayHttpReader,
    JsonArrayHttpReaderError,
)


class GitHubReleaseAccessibilityValidator:
    _API_HEADERS = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "trackstate-ts-710-test",
    }
    _STABLE_TAG_PATTERN = re.compile(r"^v\d+\.\d+\.\d+$")

    def __init__(
        self,
        config: GitHubReleaseAccessibilityConfig,
        *,
        json_array_http_reader: JsonArrayHttpReader,
        release_page_factory: callable,
    ) -> None:
        self._config = config
        self._json_array_http_reader = json_array_http_reader
        self._release_page_factory = release_page_factory

    def validate(self) -> GitHubReleaseAccessibilityObservation:
        tag_name = self._config.release_tag or self._discover_release_tag()
        with self._release_page_factory() as release_page:
            release_page_url = release_page.open_release(
                repository=self._config.repository,
                tag_name=tag_name,
            )
            return release_page.observe_accessibility(
                repository=self._config.repository,
                tag_name=tag_name,
                release_page_url=release_page_url,
                screenshot_path=self._config.screenshot_path,
            )

    def _discover_release_tag(self) -> str:
        try:
            response = self._json_array_http_reader.read_json_array(
                url=self._config.releases_api_url,
                headers=self._API_HEADERS,
                timeout_seconds=30,
            )
        except JsonArrayHttpReaderError as error:
            raise AssertionError(
                "TS-710 could not query the public GitHub Releases API to discover the "
                "latest stable `v*` release.\n"
                f"Endpoint: {self._config.releases_api_url}\n"
                f"Error: {error}",
            ) from error

        if response.status_code != 200:
            raise AssertionError(
                "TS-710 requires the public GitHub Releases API to return HTTP 200.\n"
                f"Endpoint: {self._config.releases_api_url}\n"
                f"Observed status: {response.status_code}",
            )

        for entry in response.payload:
            if not isinstance(entry, dict):
                continue
            if bool(entry.get("draft")) or bool(entry.get("prerelease")):
                continue
            tag_name = str(entry.get("tag_name", "")).strip()
            if self._STABLE_TAG_PATTERN.fullmatch(tag_name) is None:
                continue
            return tag_name

        raise AssertionError(
            "TS-710 could not find a published stable `v<major>.<minor>.<patch>` "
            "release to verify on the live GitHub Releases page.\n"
            f"Endpoint: {self._config.releases_api_url}",
        )

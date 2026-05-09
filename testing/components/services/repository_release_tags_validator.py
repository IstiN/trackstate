from __future__ import annotations

import json
import re
from urllib import error as urllib_error
from urllib import request as urllib_request

from testing.core.config.repository_release_tags_config import (
    RepositoryReleaseTagsConfig,
)
from testing.core.interfaces.repository_release_tags_probe import (
    RepositoryReleaseTagsObservation,
)
from testing.core.interfaces.url_text_reader import UrlTextReader


class RepositoryReleaseTagsValidator:
    _STABLE_VERSION_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
    _API_HEADERS = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "trackstate-ts-229-test",
    }
    _HTML_HEADERS = {
        "User-Agent": "trackstate-ts-229-test",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(
        self,
        config: RepositoryReleaseTagsConfig,
        *,
        url_text_reader: UrlTextReader,
    ) -> None:
        self._config = config
        self._url_text_reader = url_text_reader

    def validate(self) -> RepositoryReleaseTagsObservation:
        releases_status_code, releases_payload = self._read_json_array(
            self._config.releases_api_url
        )
        tags_status_code, tags_payload = self._read_json_array(self._config.tags_api_url)

        release_tag_names = self._extract_release_tag_names(releases_payload)
        tag_names = self._extract_tag_names(tags_payload)
        stable_release_versions = self._stable_versions(release_tag_names)
        stable_tag_versions = self._stable_versions(tag_names)
        common_stable_versions = self._common_stable_versions(
            stable_release_versions=stable_release_versions,
            stable_tag_versions=stable_tag_versions,
        )
        latest_common_stable_version = (
            common_stable_versions[-1] if common_stable_versions else None
        )

        releases_page_text = self._url_text_reader.read_text(
            url=self._config.releases_page_url,
            headers=self._HTML_HEADERS,
            timeout_seconds=30,
        )
        tags_page_text = self._url_text_reader.read_text(
            url=self._config.tags_page_url,
            headers=self._HTML_HEADERS,
            timeout_seconds=30,
        )

        return RepositoryReleaseTagsObservation(
            repository=self._config.repository,
            releases_api_url=self._config.releases_api_url,
            tags_api_url=self._config.tags_api_url,
            releases_status_code=releases_status_code,
            tags_status_code=tags_status_code,
            release_tag_names=release_tag_names,
            tag_names=tag_names,
            stable_release_versions=stable_release_versions,
            stable_tag_versions=stable_tag_versions,
            common_stable_versions=common_stable_versions,
            latest_common_stable_version=latest_common_stable_version,
            releases_page_url=self._config.releases_page_url,
            tags_page_url=self._config.tags_page_url,
            releases_page_text=releases_page_text,
            tags_page_text=tags_page_text,
        )

    def _read_json_array(self, url: str) -> tuple[int | None, list[object]]:
        request = urllib_request.Request(url, headers=self._API_HEADERS)
        try:
            with urllib_request.urlopen(request, timeout=30) as response:
                status_code = response.getcode()
                body = response.read().decode("utf-8")
        except urllib_error.HTTPError as error:
            status_code = error.code
            body = error.read().decode("utf-8", errors="replace")
        except urllib_error.URLError as error:
            raise RuntimeError(f"GET {url} failed: {error.reason}") from error

        payload = json.loads(body or "[]")
        if not isinstance(payload, list):
            return status_code, []
        return status_code, payload

    def _extract_release_tag_names(self, payload: list[object]) -> list[str]:
        names: list[str] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            tag_name = str(entry.get("tag_name", "")).strip()
            if tag_name:
                names.append(tag_name)
        return names

    def _extract_tag_names(self, payload: list[object]) -> list[str]:
        names: list[str] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name", "")).strip()
            if name:
                names.append(name)
        return names

    def _stable_versions(self, versions: list[str]) -> list[str]:
        stable = {
            version
            for version in versions
            if self._STABLE_VERSION_PATTERN.match(version) is not None
        }
        return sorted(stable, key=self._version_key)

    def _common_stable_versions(
        self,
        *,
        stable_release_versions: list[str],
        stable_tag_versions: list[str],
    ) -> list[str]:
        common = set(stable_release_versions).intersection(stable_tag_versions)
        return sorted(common, key=self._version_key)

    def _version_key(self, version: str) -> tuple[int, int, int]:
        match = self._STABLE_VERSION_PATTERN.match(version)
        if match is None:
            return (0, 0, 0)
        return (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
        )

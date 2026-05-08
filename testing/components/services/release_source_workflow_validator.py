from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from testing.core.config.release_source_workflow_config import (
    ReleaseSourceWorkflowConfig,
)


@dataclass(frozen=True)
class ReleaseRefObservation:
    kind: str
    name: str
    sha: str | None
    html_url: str


@dataclass(frozen=True)
class ReleaseSourceWorkflowObservation:
    repository: str
    default_branch: str
    workflow_path: str
    default_branch_has_workflow: bool
    releases_page_url: str
    tags_page_url: str
    releases: list[ReleaseRefObservation]
    tags: list[ReleaseRefObservation]
    selected_ref: ReleaseRefObservation | None
    selected_ref_has_workflow: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReleaseSourceWorkflowValidator:
    def __init__(self, config: ReleaseSourceWorkflowConfig) -> None:
        self._config = config

    def validate(self) -> ReleaseSourceWorkflowObservation:
        releases = self._list_releases()
        tags = self._list_tags()
        selected_ref = releases[0] if releases else (tags[0] if tags else None)

        return ReleaseSourceWorkflowObservation(
            repository=self._config.repository,
            default_branch=self._config.default_branch,
            workflow_path=self._config.workflow_path,
            default_branch_has_workflow=self._workflow_exists(
                self._config.default_branch
            ),
            releases_page_url=self._config.releases_page_url,
            tags_page_url=self._config.tags_page_url,
            releases=releases,
            tags=tags,
            selected_ref=selected_ref,
            selected_ref_has_workflow=(
                self._workflow_exists(selected_ref.name) if selected_ref else False
            ),
        )

    def _list_releases(self) -> list[ReleaseRefObservation]:
        payload = self._read_json(self._config.releases_api_endpoint)
        if not isinstance(payload, list):
            return []

        releases: list[ReleaseRefObservation] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            tag_name = str(entry.get("tag_name", "")).strip()
            if not tag_name:
                continue
            releases.append(
                ReleaseRefObservation(
                    kind="release",
                    name=tag_name,
                    sha=None,
                    html_url=str(
                        entry.get(
                            "html_url",
                            f"https://github.com/{self._config.repository}/releases/tag/{tag_name}",
                        )
                    ),
                )
            )
        return releases

    def _list_tags(self) -> list[ReleaseRefObservation]:
        payload = self._read_json(self._config.tags_api_endpoint)
        if not isinstance(payload, list):
            return []

        tags: list[ReleaseRefObservation] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name", "")).strip()
            commit = entry.get("commit")
            sha = None
            if isinstance(commit, dict):
                raw_sha = commit.get("sha")
                if raw_sha is not None:
                    sha = str(raw_sha)
            if not name:
                continue
            tags.append(
                ReleaseRefObservation(
                    kind="tag",
                    name=name,
                    sha=sha,
                    html_url=f"https://github.com/{self._config.repository}/tree/{quote(name, safe='')}",
                )
            )
        return tags

    def _workflow_exists(self, ref: str) -> bool:
        path = quote(self._config.workflow_path, safe="/")
        request = self._build_request(
            f"https://api.github.com/repos/{self._config.repository}/contents/{path}?ref={quote(ref, safe='')}"
        )
        try:
            with urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 404:
                return False
            raise

        return isinstance(payload, dict) and str(payload.get("type", "")).strip() == "file"

    def _read_json(self, endpoint: str) -> object:
        request = self._build_request(f"https://api.github.com{endpoint}")
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def _build_request(self, url: str) -> Request:
        return Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "trackstate-test-automation",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.parse import quote

from testing.core.config.release_source_workflow_config import (
    ReleaseSourceWorkflowConfig,
)
from testing.core.interfaces.github_api_client import (
    GitHubApiClient,
    GitHubApiClientError,
)
from testing.core.interfaces.release_source_workflow_probe import (
    ReleaseRefObservation,
    ReleaseSourceWorkflowObservation,
)


class ReleaseSourceWorkflowError(RuntimeError):
    pass


class ReleaseSourceWorkflowValidator:
    def __init__(
        self,
        config: ReleaseSourceWorkflowConfig,
        *,
        github_api_client: GitHubApiClient,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client

    def validate(self) -> ReleaseSourceWorkflowObservation:
        releases = self._list_releases()
        tags = self._list_tags()
        selected_ref = self._select_latest_reference(releases, tags)

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
                    observed_at=self._normalize_timestamp(
                        entry.get("published_at") or entry.get("created_at")
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
                    observed_at=self._tag_observed_at(sha),
                )
            )
        return tags

    def _select_latest_reference(
        self,
        releases: list[ReleaseRefObservation],
        tags: list[ReleaseRefObservation],
    ) -> ReleaseRefObservation | None:
        candidates = [*releases, *tags]
        if not candidates:
            return None

        latest = max(candidates, key=self._selection_key)
        return latest

    def _selection_key(self, ref: ReleaseRefObservation) -> tuple[int, datetime, str]:
        observed_at = self._parse_timestamp(ref.observed_at)
        return (
            1 if observed_at is not None else 0,
            observed_at or datetime.min.replace(tzinfo=timezone.utc),
            ref.name,
        )

    def _tag_observed_at(self, sha: str | None) -> str | None:
        if not sha:
            return None

        payload = self._read_json(
            f"/repos/{self._config.repository}/commits/{quote(sha, safe='')}"
        )
        if not isinstance(payload, dict):
            return None

        commit = payload.get("commit")
        if not isinstance(commit, dict):
            return None

        committer = commit.get("committer")
        if isinstance(committer, dict):
            normalized = self._normalize_timestamp(committer.get("date"))
            if normalized:
                return normalized

        author = commit.get("author")
        if isinstance(author, dict):
            return self._normalize_timestamp(author.get("date"))
        return None

    def _workflow_exists(self, ref: str) -> bool:
        path = quote(self._config.workflow_path, safe="/")
        try:
            payload = self._read_json(
                f"/repos/{self._config.repository}/contents/{path}?ref={quote(ref, safe='')}"
            )
        except ReleaseSourceWorkflowError as error:
            if self._is_not_found(error):
                return False
            raise

        return isinstance(payload, dict) and str(payload.get("type", "")).strip() == "file"

    def _read_json(self, endpoint: str) -> object:
        try:
            response_text = self._github_api_client.request_text(endpoint=endpoint)
        except GitHubApiClientError as error:
            raise ReleaseSourceWorkflowError(str(error)) from error
        return json.loads(response_text)

    @staticmethod
    def _normalize_timestamp(value: object) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None

        parsed = ReleaseSourceWorkflowValidator._parse_timestamp(value)
        if parsed is None:
            return value.strip()
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _parse_timestamp(value: str | None) -> datetime | None:
        if not value:
            return None

        normalized = value.strip()
        if not normalized:
            return None
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _is_not_found(error: ReleaseSourceWorkflowError) -> bool:
        message = str(error)
        return "HTTP 404" in message or "Not Found" in message

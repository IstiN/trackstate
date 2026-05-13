from __future__ import annotations

import base64
import json
import os
import urllib.error
from urllib.parse import quote
import urllib.request
from dataclasses import dataclass
from typing import Iterable

from testing.core.config.live_setup_test_config import (
    LiveSetupTestConfig,
    load_live_setup_test_config,
)
from testing.core.models.hosted_repository_file import HostedRepositoryFile


@dataclass(frozen=True)
class LiveHostedRepositoryMetadata:
    repository: str
    ref: str
    project_key: str
    project_name: str
    issue_types: list[str]
    statuses: list[str]
    fields: list[str]
    versions: list[str]
    components: list[str]


@dataclass(frozen=True)
class GitHubAuthenticatedUser:
    login: str
    display_name: str


@dataclass(frozen=True)
class LiveHostedIssueFixture:
    key: str
    path: str
    summary: str
    description: str
    priority_id: str
    acceptance_criteria: list[str]
    attachment_paths: list[str]
    comment_paths: list[str]
    comment_bodies: list[str]


@dataclass(frozen=True)
class LiveHostedProjectLocaleConfiguration:
    project_path: str
    default_locale: str
    supported_locales: list[str]


@dataclass(frozen=True)
class LiveHostedCatalogEntry:
    id: str
    name: str


@dataclass(frozen=True)
class LiveHostedLocaleState:
    project_path: str
    locale: str
    supported_locales: list[str]
    locale_present: bool
    payload: dict[str, object]


@dataclass(frozen=True)
class LiveHostedReleaseAsset:
    id: int
    name: str


@dataclass(frozen=True)
class LiveHostedRelease:
    id: int
    tag_name: str
    name: str
    assets: list[LiveHostedReleaseAsset]
    body: str = ""
    draft: bool = False
    prerelease: bool = False
    target_commitish: str = ""


class LiveSetupRepositoryService:
    def __init__(
        self,
        config: LiveSetupTestConfig | None = None,
        token: str | None = None,
    ) -> None:
        self.config = config or load_live_setup_test_config()
        self.repository = self.config.repository
        self.ref = self.config.ref
        self.token = token or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")

    def fetch_demo_metadata(self) -> LiveHostedRepositoryMetadata:
        project = self._read_repo_json("DEMO/project.json")
        return LiveHostedRepositoryMetadata(
            repository=self.repository,
            ref=self.ref,
            project_key=str(project.get("key", "DEMO")),
            project_name=str(project.get("name", "TrackState Project")),
            issue_types=self._read_config_names("DEMO/config/issue-types.json"),
            statuses=self._read_config_names("DEMO/config/statuses.json"),
            fields=self._read_config_names("DEMO/config/fields.json"),
            versions=self._read_config_names("DEMO/config/versions.json"),
            components=self._read_config_names("DEMO/config/components.json"),
        )

    def fetch_authenticated_user(self) -> GitHubAuthenticatedUser:
        if not self.token:
            raise RuntimeError(
                "TS-70 requires GH_TOKEN or GITHUB_TOKEN to verify the authenticated GitHub account.",
            )

        response = self._read_json("/user")
        return GitHubAuthenticatedUser(
            login=str(response.get("login", "github")),
            display_name=str(response.get("name", "")),
        )

    def fetch_issue_fixture(self, issue_path: str) -> LiveHostedIssueFixture:
        entries = self._read_repo_directory(issue_path)
        issue_key = issue_path.rstrip("/").split("/")[-1]
        main_markdown = self._read_repo_text(f"{issue_path}/main.md")
        summary = self._front_matter_value(main_markdown, key="summary")
        entry_names = {
            str(entry.get("name", ""))
            for entry in entries
            if str(entry.get("name", "")).strip()
        }
        attachment_paths = (
            [
                str(entry["path"])
                for entry in self._read_repo_directory(f"{issue_path}/attachments")
                if entry.get("type") == "file"
            ]
            if "attachments" in entry_names
            else []
        )
        comment_paths = (
            [
                str(entry["path"])
                for entry in self._read_repo_directory(f"{issue_path}/comments")
                if entry.get("type") == "file"
            ]
            if "comments" in entry_names
            else []
        )
        acceptance_markdown = (
            self._read_repo_text(f"{issue_path}/acceptance_criteria.md")
            if "acceptance_criteria.md" in entry_names
            else ""
        )
        return LiveHostedIssueFixture(
            key=issue_key,
            path=issue_path,
            summary=summary or issue_key,
            description=self._markdown_section(main_markdown, heading="Description"),
            priority_id=self._front_matter_value(main_markdown, key="priority") or "",
            acceptance_criteria=self._markdown_bullets(acceptance_markdown),
            attachment_paths=attachment_paths,
            comment_paths=comment_paths,
            comment_bodies=[
                self._markdown_body(self._read_repo_text(path)) for path in comment_paths
            ],
        )

    def fetch_issue_type_config_entries(
        self,
        project_key: str = "DEMO",
    ) -> list[dict[str, object]]:
        payload = self._read_repo_json(f"{project_key}/config/issue-types.json")
        if not isinstance(payload, list):
            raise RuntimeError(
                f"GitHub response for {project_key}/config/issue-types.json was not a list.",
            )
        return [entry for entry in payload if isinstance(entry, dict)]

    def fetch_workflow_config_map(
        self,
        project_key: str = "DEMO",
    ) -> dict[str, dict[str, object]]:
        payload = self._read_repo_json(f"{project_key}/config/workflows.json")
        if not isinstance(payload, dict):
            raise RuntimeError(
                f"GitHub response for {project_key}/config/workflows.json was not an object.",
            )
        return {
            str(key): value
            for key, value in payload.items()
            if isinstance(key, str) and isinstance(value, dict)
        }

    def fetch_project_locale_configuration(
        self,
        project_path: str,
    ) -> LiveHostedProjectLocaleConfiguration:
        project = self._read_project_json(project_path)
        supported_locales = [
            str(value).strip()
            for value in project.get("supportedLocales", [])
            if str(value).strip()
        ]
        return LiveHostedProjectLocaleConfiguration(
            project_path=project_path,
            default_locale=str(project.get("defaultLocale", "en")),
            supported_locales=supported_locales,
        )

    def fetch_catalog_entries(
        self,
        project_path: str,
        catalog_name: str,
    ) -> list[LiveHostedCatalogEntry]:
        values = self._read_repo_json(f"{project_path}/config/{catalog_name}.json")
        if not isinstance(values, list):
            raise RuntimeError(
                f"GitHub response for {project_path}/config/{catalog_name}.json was not a list.",
            )
        return [
            LiveHostedCatalogEntry(id=entry_id, name=name)
            for entry in values
            if isinstance(entry, dict)
            for entry_id, name in [
                (
                    str(entry.get("id", "")).strip(),
                    str(entry.get("name", "")).strip(),
                ),
            ]
            if entry_id and name
        ]

    def fetch_repo_file(self, path: str) -> HostedRepositoryFile:
        response = self._read_json(
            f"/repos/{self.repository}/contents/{path}?ref={self.ref}",
        )
        encoded = str(response.get("content", "")).replace("\n", "")
        if not encoded:
            raise RuntimeError(f"GitHub response for {path} did not include content.")
        sha = str(response.get("sha", "")).strip()
        if not sha:
            raise RuntimeError(f"GitHub response for {path} did not include a blob SHA.")
        return HostedRepositoryFile(
            path=path,
            sha=sha,
            content=base64.b64decode(encoded).decode("utf-8"),
        )

    def fetch_repo_text(self, path: str) -> str:
        return self.fetch_repo_file(path).content

    def write_repo_text(self, path: str, *, content: str, message: str) -> None:
        sha: str | None = None
        try:
            sha = self.fetch_repo_file(path).sha
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise

        payload: dict[str, object] = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": self.ref,
        }
        if sha is not None:
            payload["sha"] = sha

        request = urllib.request.Request(
            f"https://api.github.com/repos/{self.repository}/contents/{path}",
            data=json.dumps(payload).encode("utf-8"),
            method="PUT",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                **(
                    {"Authorization": f"Bearer {self.token}"}
                    if self.token
                    else {}
                ),
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status not in (200, 201):
                raise RuntimeError(
                    f"GitHub write for {path} returned unexpected status {response.status}.",
                )

    def delete_repo_file(self, path: str, *, message: str) -> None:
        existing = self.fetch_repo_file(path)
        payload = {
            "message": message,
            "sha": existing.sha,
            "branch": self.ref,
        }
        request = urllib.request.Request(
            f"https://api.github.com/repos/{self.repository}/contents/{path}",
            data=json.dumps(payload).encode("utf-8"),
            method="DELETE",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                **(
                    {"Authorization": f"Bearer {self.token}"}
                    if self.token
                    else {}
                ),
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status not in (200, 202):
                raise RuntimeError(
                    f"GitHub delete for {path} returned unexpected status {response.status}.",
                )

    def fetch_locale_payload(self, project_path: str, locale: str) -> dict[str, object]:
        try:
            payload = self._read_repo_json(f"{project_path}/config/i18n/{locale}.json")
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return {}
            raise
        if not isinstance(payload, dict):
            raise RuntimeError(
                f"GitHub response for {project_path}/config/i18n/{locale}.json was not an object.",
            )
        return payload

    def fetch_locale_state(self, project_path: str, locale: str) -> LiveHostedLocaleState:
        locale_configuration = self.fetch_project_locale_configuration(project_path)
        locale_present = locale in locale_configuration.supported_locales
        payload = self.fetch_locale_payload(project_path, locale) if locale_present else {}
        return LiveHostedLocaleState(
            project_path=project_path,
            locale=locale,
            supported_locales=locale_configuration.supported_locales,
            locale_present=locale_present,
            payload=payload,
        )

    def list_issue_paths(self, root_path: str = "DEMO") -> list[str]:
        issue_paths: list[str] = []
        pending_paths = [root_path]

        while pending_paths:
            path = pending_paths.pop()
            entries = self._read_repo_directory(path)
            entry_names = {
                str(entry.get("name", ""))
                for entry in entries
                if str(entry.get("name", "")).strip()
            }
            if "main.md" in entry_names:
                issue_paths.append(path)
            for entry in entries:
                if entry.get("type") == "dir":
                    pending_paths.append(str(entry["path"]))

        return sorted(issue_paths)

    def fetch_release_by_tag(self, tag_name: str) -> LiveHostedRelease | None:
        try:
            payload = self._read_json(
                f"/repos/{self.repository}/releases/tags/{tag_name}",
            )
        except urllib.error.HTTPError as error:
            if error.code == 404:
                releases = self._read_json(
                    f"/repos/{self.repository}/releases?per_page=100",
                )
                if not isinstance(releases, list):
                    raise RuntimeError(
                        "GitHub response for repository releases was not a list.",
                    )
                for candidate in releases:
                    if not isinstance(candidate, dict):
                        continue
                    if str(candidate.get("tag_name", "")).strip() == tag_name:
                        return self._parse_release(candidate, fallback_tag_name=tag_name)
                return None
            raise
        if not isinstance(payload, dict):
            raise RuntimeError(
                f"GitHub response for release tag {tag_name} was not an object.",
            )
        return self._parse_release(payload, fallback_tag_name=tag_name)

    def fetch_releases_by_tag_any_state(
        self,
        tag_name: str,
        *,
        max_pages: int = 5,
    ) -> list[LiveHostedRelease]:
        matches_by_id: dict[int, LiveHostedRelease] = {}
        for page in range(1, max_pages + 1):
            releases = self._read_json(
                f"/repos/{self.repository}/releases?per_page=100&page={page}",
            )
            if not isinstance(releases, list):
                raise RuntimeError("GitHub response for repository releases was not a list.")
            if not releases:
                break
            for candidate in releases:
                if not isinstance(candidate, dict):
                    continue
                if str(candidate.get("tag_name", "")).strip() != tag_name:
                    continue
                release_id = int(candidate.get("id", 0))
                if release_id <= 0 or release_id in matches_by_id:
                    continue
                detail = self._read_json(f"/repos/{self.repository}/releases/{release_id}")
                matches_by_id[release_id] = self._parse_release(
                    detail,
                    context=f"release {release_id}",
                )
        return list(matches_by_id.values())

    def fetch_release_by_tag_any_state(self, tag_name: str) -> LiveHostedRelease | None:
        matches = self.fetch_releases_by_tag_any_state(tag_name)
        if matches:
            return matches[0]
        return self.fetch_release_by_tag(tag_name)

    def download_release_asset_bytes(self, asset_id: int) -> bytes:
        request = urllib.request.Request(
            f"https://api.github.com/repos/{self.repository}/releases/assets/{asset_id}",
            headers={
                "Accept": "application/octet-stream",
                "X-GitHub-Api-Version": "2022-11-28",
                **(
                    {"Authorization": f"Bearer {self.token}"}
                    if self.token
                    else {}
                ),
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"GitHub release asset download for {asset_id} returned unexpected "
                    f"status {response.status}.",
                )
            return response.read()

    def delete_release_asset(self, asset_id: int) -> None:
        request = urllib.request.Request(
            f"https://api.github.com/repos/{self.repository}/releases/assets/{asset_id}",
            method="DELETE",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                **(
                    {"Authorization": f"Bearer {self.token}"}
                    if self.token
                    else {}
                ),
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status != 204:
                raise RuntimeError(
                    "GitHub delete for release asset "
                    f"{asset_id} returned unexpected status {response.status}.",
                )

    def delete_release(self, release_id: int) -> None:
        request = urllib.request.Request(
            f"https://api.github.com/repos/{self.repository}/releases/{release_id}",
            method="DELETE",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                **(
                    {"Authorization": f"Bearer {self.token}"}
                    if self.token
                    else {}
                ),
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status != 204:
                raise RuntimeError(
                    f"GitHub delete for release {release_id} returned unexpected status "
                    f"{response.status}.",
                )

    def create_release(
        self,
        *,
        tag_name: str,
        name: str,
        body: str = "",
        target_commitish: str | None = None,
        draft: bool = True,
        prerelease: bool = False,
    ) -> LiveHostedRelease:
        payload = self._write_json(
            f"/repos/{self.repository}/releases",
            payload={
                "tag_name": tag_name,
                "name": name,
                "body": body,
                "target_commitish": target_commitish or self.ref,
                "draft": draft,
                "prerelease": prerelease,
            },
            method="POST",
        )
        return self._parse_release(payload, context=f"create release {tag_name}")

    def update_release(
        self,
        release_id: int,
        *,
        name: str | None = None,
        body: str | None = None,
        target_commitish: str | None = None,
        draft: bool | None = None,
        prerelease: bool | None = None,
    ) -> LiveHostedRelease:
        payload: dict[str, object] = {}
        if name is not None:
            payload["name"] = name
        if body is not None:
            payload["body"] = body
        if target_commitish is not None:
            payload["target_commitish"] = target_commitish
        if draft is not None:
            payload["draft"] = draft
        if prerelease is not None:
            payload["prerelease"] = prerelease
        if not payload:
            raise ValueError("update_release requires at least one field to update.")

        updated = self._write_json(
            f"/repos/{self.repository}/releases/{release_id}",
            payload=payload,
            method="PATCH",
        )
        return self._parse_release(updated, context=f"update release {release_id}")

    def update_release_name(self, release_id: int, *, name: str) -> LiveHostedRelease:
        return self.update_release(release_id, name=name)

    def upload_release_asset(
        self,
        *,
        release_id: int,
        asset_name: str,
        content_type: str,
        content: bytes,
    ) -> LiveHostedReleaseAsset:
        request = urllib.request.Request(
            (
                f"https://uploads.github.com/repos/{self.repository}/releases/"
                f"{release_id}/assets?name={quote(asset_name)}"
            ),
            data=content,
            method="POST",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": content_type,
                "Content-Length": str(len(content)),
                **(
                    {"Authorization": f"Bearer {self.token}"}
                    if self.token
                    else {}
                ),
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            if response.status != 201:
                raise RuntimeError(
                    f"GitHub release asset upload for {asset_name} returned unexpected "
                    f"status {response.status}.",
                )
            raw_payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(raw_payload, dict):
            raise RuntimeError(
                f"GitHub release asset upload for {asset_name} did not return an object payload.",
            )
        return LiveHostedReleaseAsset(
            id=int(raw_payload.get("id", 0)),
            name=str(raw_payload.get("name", "")).strip(),
        )
    def _read_config_names(self, path: str) -> list[str]:
        values = self._read_repo_json(path)
        return [
            str(entry["name"])
            for entry in values
            if isinstance(entry, dict) and str(entry.get("name", "")).strip()
        ]

    def _read_project_json(self, project_path: str) -> dict[str, object]:
        project = self._read_repo_json(f"{project_path}/project.json")
        if not isinstance(project, dict):
            raise RuntimeError(f"GitHub response for {project_path}/project.json was not an object.")
        return project

    def _read_repo_directory(self, path: str) -> list[dict[str, object]]:
        response = self._read_json(
            f"/repos/{self.repository}/contents/{path}?ref={self.ref}",
        )
        if not isinstance(response, list):
            raise RuntimeError(f"GitHub response for directory {path} was not a list.")
        return [entry for entry in response if isinstance(entry, dict)]

    def _read_repo_json(self, path: str):
        response = self._read_json(
            f"/repos/{self.repository}/contents/{path}?ref={self.ref}",
        )
        encoded = str(response.get("content", "")).replace("\n", "")
        if not encoded:
            raise RuntimeError(f"GitHub response for {path} did not include content.")
        return json.loads(base64.b64decode(encoded).decode("utf-8"))

    def _read_repo_text(self, path: str) -> str:
        response = self._read_json(
            f"/repos/{self.repository}/contents/{path}?ref={self.ref}",
        )
        encoded = str(response.get("content", "")).replace("\n", "")
        if not encoded:
            raise RuntimeError(f"GitHub response for {path} did not include content.")
        return base64.b64decode(encoded).decode("utf-8")

    @staticmethod
    def _front_matter_value(markdown: str, *, key: str) -> str | None:
        in_front_matter = False
        for raw_line in markdown.splitlines():
            line = raw_line.strip()
            if line == "---":
                in_front_matter = not in_front_matter
                continue
            if not in_front_matter:
                continue
            prefix = f"{key}:"
            if line.startswith(prefix):
                return line.removeprefix(prefix).strip()
        return None

    @staticmethod
    def _markdown_section(markdown: str, *, heading: str) -> str:
        lines = markdown.splitlines()
        start_index = -1
        for index, raw_line in enumerate(lines):
            if raw_line.strip() == f"# {heading}":
                start_index = index + 1
                break
        if start_index == -1:
            return ""

        section_lines: list[str] = []
        for raw_line in lines[start_index:]:
            stripped = raw_line.strip()
            if stripped.startswith("# "):
                break
            section_lines.append(raw_line)
        return "\n".join(section_lines).strip()

    @staticmethod
    def _markdown_bullets(markdown: str) -> list[str]:
        bullets: list[str] = []
        for raw_line in markdown.splitlines():
            stripped = raw_line.strip()
            if stripped.startswith("- "):
                bullets.append(stripped.removeprefix("- ").strip())
        return bullets

    @staticmethod
    def _markdown_body(markdown: str) -> str:
        lines = markdown.splitlines()
        if not lines:
            return ""
        if lines[0].strip() != "---":
            return markdown.strip()

        end_index = -1
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                end_index = index
                break
        if end_index == -1:
            return markdown.strip()

        return "\n".join(LiveSetupRepositoryService._skip_blank_prefix(lines[end_index + 1 :]))

    @staticmethod
    def _skip_blank_prefix(lines: Iterable[str]) -> list[str]:
        collected = list(lines)
        while collected and not collected[0].strip():
            collected.pop(0)
        return collected

    def _read_json(self, path: str):
        request = urllib.request.Request(
            f"https://api.github.com{path}",
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                **(
                    {"Authorization": f"Bearer {self.token}"}
                    if self.token
                    else {}
                ),
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def _write_json(self, path: str, *, payload: dict[str, object], method: str):
        request = urllib.request.Request(
            f"https://api.github.com{path}",
            data=json.dumps(payload).encode("utf-8"),
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                **(
                    {"Authorization": f"Bearer {self.token}"}
                    if self.token
                    else {}
                ),
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def _parse_release(
        self,
        payload: object,
        *,
        context: str | None = None,
        fallback_tag_name: str = "",
    ) -> LiveHostedRelease:
        if not isinstance(payload, dict):
            release_context = context or (
                f"release tag {fallback_tag_name}" if fallback_tag_name else "release"
            )
            raise RuntimeError(f"GitHub response for {release_context} was not an object.")
        return LiveHostedRelease(
            id=int(payload.get("id", 0)),
            tag_name=str(payload.get("tag_name", "")).strip() or fallback_tag_name,
            name=str(payload.get("name", "")).strip(),
            assets=[
                LiveHostedReleaseAsset(
                    id=int(asset.get("id", 0)),
                    name=str(asset.get("name", "")).strip(),
                )
                for asset in payload.get("assets", [])
                if isinstance(asset, dict)
            ],
            body=str(payload.get("body", "")),
            draft=bool(payload.get("draft", False)),
            prerelease=bool(payload.get("prerelease", False)),
            target_commitish=str(payload.get("target_commitish", "")).strip(),
        )


LiveHostedRepositoryFile = HostedRepositoryFile

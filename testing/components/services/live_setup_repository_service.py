from __future__ import annotations

import base64
import json
import os
from typing import Iterable
import urllib.request
from dataclasses import dataclass

from testing.core.config.live_setup_test_config import (
    LiveSetupTestConfig,
    load_live_setup_test_config,
)


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

    def _read_config_names(self, path: str) -> list[str]:
        values = self._read_repo_json(path)
        return [
            str(entry["name"])
            for entry in values
            if isinstance(entry, dict) and str(entry.get("name", "")).strip()
        ]

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

from __future__ import annotations

import base64
import json
import os
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


@dataclass(frozen=True)
class GitHubAuthenticatedUser:
    login: str
    display_name: str


@dataclass(frozen=True)
class LiveHostedIssueFixture:
    key: str
    path: str
    summary: str
    attachment_paths: list[str]
    comment_paths: list[str]


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
        return LiveHostedIssueFixture(
            key=issue_key,
            path=issue_path,
            summary=summary or issue_key,
            attachment_paths=[
                str(entry["path"])
                for entry in self._read_repo_directory(f"{issue_path}/attachments")
                if entry.get("type") == "file"
            ],
            comment_paths=[
                str(entry["path"])
                for entry in self._read_repo_directory(f"{issue_path}/comments")
                if entry.get("type") == "file"
            ],
        )

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

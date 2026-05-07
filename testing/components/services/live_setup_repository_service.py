from __future__ import annotations

import base64
import json
import os
import urllib.request
from dataclasses import dataclass


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


class LiveSetupRepositoryService:
    def __init__(
        self,
        repository: str = "IstiN/trackstate-setup",
        ref: str = "main",
        token: str | None = None,
    ) -> None:
        self.repository = repository
        self.ref = ref
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

    def _read_config_names(self, path: str) -> list[str]:
        values = self._read_repo_json(path)
        return [
            str(entry["name"])
            for entry in values
            if isinstance(entry, dict) and str(entry.get("name", "")).strip()
        ]

    def _read_repo_json(self, path: str):
        response = self._read_json(
            f"/repos/{self.repository}/contents/{path}?ref={self.ref}",
        )
        encoded = str(response.get("content", "")).replace("\n", "")
        if not encoded:
            raise RuntimeError(f"GitHub response for {path} did not include content.")
        return json.loads(base64.b64decode(encoded).decode("utf-8"))

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

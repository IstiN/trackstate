from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any
import urllib.error
import urllib.request


@dataclass(frozen=True)
class HostedRepositoryFile:
    path: str
    sha: str
    content: str


@dataclass(frozen=True)
class HostedCommitObservation:
    sha: str
    message: str
    parent_shas: tuple[str, ...]
    changed_files: tuple[str, ...]


class HostedProjectSettingsRepositoryService:
    def __init__(
        self,
        *,
        repository: str,
        branch: str = "main",
        token: str | None = None,
    ) -> None:
        self.repository = repository
        self.branch = branch
        self.token = token or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise RuntimeError(
                "TS-409 requires GH_TOKEN or GITHUB_TOKEN to inspect and restore "
                "the hosted repository.",
            )

    def fetch_file(self, path: str, *, ref: str | None = None) -> HostedRepositoryFile:
        response = self._request_json(
            "GET",
            f"/repos/{self.repository}/contents/{path}?ref={ref or self.branch}",
        )
        encoded = str(response.get("content", "")).replace("\n", "")
        if not encoded:
            raise RuntimeError(f"GitHub did not return content for {path}.")
        return HostedRepositoryFile(
            path=path,
            sha=str(response.get("sha", "")),
            content=base64.b64decode(encoded).decode("utf-8"),
        )

    def branch_head_sha(self) -> str:
        response = self._request_json(
            "GET",
            f"/repos/{self.repository}/git/ref/heads/{self.branch}",
        )
        return str(((response.get("object") or {}).get("sha") or "")).strip()

    def wait_for_head_change(self, previous_sha: str, *, attempts: int = 20) -> str:
        for _ in range(attempts):
            current_sha = self.branch_head_sha()
            if current_sha and current_sha != previous_sha:
                return current_sha
        raise AssertionError(
            "Step 4 failed: saving the Settings changes never produced a new branch "
            "head commit within the polling window.\n"
            f"Previous head: {previous_sha}",
        )

    def fetch_commit(self, sha: str) -> HostedCommitObservation:
        response = self._request_json("GET", f"/repos/{self.repository}/commits/{sha}")
        parents = tuple(
            str(parent.get("sha", ""))
            for parent in response.get("parents", [])
            if isinstance(parent, dict)
        )
        files = tuple(
            str(file_info.get("filename", ""))
            for file_info in response.get("files", [])
            if isinstance(file_info, dict)
        )
        return HostedCommitObservation(
            sha=sha,
            message=str(((response.get("commit") or {}).get("message") or "")).strip(),
            parent_shas=parents,
            changed_files=files,
        )

    def restore_settings(
        self,
        *,
        statuses_content: str,
        workflows_content: str,
        message: str,
    ) -> str:
        parent_sha = self.branch_head_sha()
        parent_commit = self._request_json(
            "GET",
            f"/repos/{self.repository}/git/commits/{parent_sha}",
        )
        base_tree_sha = str(parent_commit.get("tree", {}).get("sha", "")).strip()
        if not base_tree_sha:
            raise RuntimeError("Could not resolve the base tree for cleanup.")

        statuses_blob_sha = self._create_blob(statuses_content)
        workflows_blob_sha = self._create_blob(workflows_content)
        tree_sha = self._create_tree(
            base_tree_sha=base_tree_sha,
            entries=(
                ("DEMO/config/statuses.json", statuses_blob_sha),
                ("DEMO/config/workflows.json", workflows_blob_sha),
            ),
        )
        commit_sha = self._create_commit(
            message=message,
            tree_sha=tree_sha,
            parent_sha=parent_sha,
        )
        self._update_ref(commit_sha)
        return commit_sha

    def _create_blob(self, content: str) -> str:
        response = self._request_json(
            "POST",
            f"/repos/{self.repository}/git/blobs",
            body={"content": content, "encoding": "utf-8"},
        )
        return str(response.get("sha", "")).strip()

    def _create_tree(
        self,
        *,
        base_tree_sha: str,
        entries: tuple[tuple[str, str], ...],
    ) -> str:
        response = self._request_json(
            "POST",
            f"/repos/{self.repository}/git/trees",
            body={
                "base_tree": base_tree_sha,
                "tree": [
                    {
                        "path": path,
                        "mode": "100644",
                        "type": "blob",
                        "sha": blob_sha,
                    }
                    for path, blob_sha in entries
                ],
            },
        )
        return str(response.get("sha", "")).strip()

    def _create_commit(
        self,
        *,
        message: str,
        tree_sha: str,
        parent_sha: str,
    ) -> str:
        response = self._request_json(
            "POST",
            f"/repos/{self.repository}/git/commits",
            body={
                "message": message,
                "tree": tree_sha,
                "parents": [parent_sha],
            },
        )
        return str(response.get("sha", "")).strip()

    def _update_ref(self, sha: str) -> None:
        self._request_json(
            "PATCH",
            f"/repos/{self.repository}/git/refs/heads/{self.branch}",
            body={"sha": sha, "force": False},
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = None
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            f"https://api.github.com{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API {method} {path} failed with HTTP {error.code}.\n"
                f"Response body:\n{details}",
            ) from error

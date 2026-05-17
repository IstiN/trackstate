from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import quote

from testing.core.config.live_setup_test_config import (
    LiveSetupTestConfig,
    load_live_setup_test_config,
)


@dataclass(frozen=True)
class LiveHostedGitRef:
    ref: str
    sha: str


class LiveSetupRepositoryGitRefService:
    def __init__(
        self,
        config: LiveSetupTestConfig | None = None,
        token: str | None = None,
    ) -> None:
        self.config = config or load_live_setup_test_config()
        self.repository = self.config.repository
        self.ref = self.config.ref
        self.token = token or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")

    def fetch_branch_head_sha(self, branch: str) -> str:
        ref = self._fetch_git_ref(f"heads/{branch}")
        if ref is None or not ref.sha:
            raise RuntimeError(
                f"Could not resolve branch head SHA for {self.repository}@{branch}.",
            )
        return ref.sha

    def fetch_branch_ref(self, branch: str) -> LiveHostedGitRef | None:
        return self._fetch_git_ref(f"heads/{branch}")

    def create_branch_ref(self, *, branch: str, sha: str) -> LiveHostedGitRef:
        payload = self._write_json(
            f"/repos/{self.repository}/git/refs",
            payload={"ref": f"refs/heads/{branch}", "sha": sha},
            method="POST",
        )
        return self._parse_git_ref(payload, context=f"branch {branch}")

    def delete_branch_ref(self, branch: str) -> None:
        self._delete_git_ref(f"heads/{branch}", context=f"branch {branch}")

    def fetch_tag_ref(self, tag_name: str) -> LiveHostedGitRef | None:
        return self._fetch_git_ref(f"tags/{tag_name}")

    def fetch_tag_sha(self, tag_name: str) -> str | None:
        ref = self.fetch_tag_ref(tag_name)
        return ref.sha if ref is not None else None

    def create_tag_ref(self, *, tag_name: str, sha: str) -> LiveHostedGitRef:
        payload = self._write_json(
            f"/repos/{self.repository}/git/refs",
            payload={"ref": f"refs/tags/{tag_name}", "sha": sha},
            method="POST",
        )
        return self._parse_git_ref(payload, context=f"tag {tag_name}")

    def delete_tag_ref(self, tag_name: str) -> None:
        self._delete_git_ref(f"tags/{tag_name}", context=f"tag {tag_name}")

    def _delete_git_ref(self, suffix: str, *, context: str) -> None:
        request = urllib.request.Request(
            f"https://api.github.com/repos/{self.repository}/git/refs/"
            f"{quote(suffix, safe='/')}",
            method="DELETE",
            headers=self._headers(),
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                if response.status != 204:
                    raise RuntimeError(
                        "GitHub delete for git ref "
                        f"{context} returned unexpected status {response.status}.",
                    )
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API DELETE /repos/{self.repository}/git/refs/{suffix} "
                f"failed with HTTP {error.code}.\nResponse body:\n{details}",
            ) from error

    def _fetch_git_ref(self, suffix: str) -> LiveHostedGitRef | None:
        path = f"/repos/{self.repository}/git/ref/{quote(suffix, safe='/')}"
        try:
            payload = self._read_json(path)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise
        return self._parse_git_ref(payload, context=suffix)

    def _read_json(self, path: str) -> object:
        request = urllib.request.Request(
            f"https://api.github.com{path}",
            headers=self._headers(),
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def _write_json(self, path: str, *, payload: dict[str, object], method: str) -> object:
        request = urllib.request.Request(
            f"https://api.github.com{path}",
            data=json.dumps(payload).encode("utf-8"),
            method=method,
            headers={
                **self._headers(),
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            **(
                {"Authorization": f"Bearer {self.token}"}
                if self.token
                else {}
            ),
        }

    @staticmethod
    def _parse_git_ref(payload: object, *, context: str) -> LiveHostedGitRef:
        if not isinstance(payload, dict):
            raise RuntimeError(
                f"GitHub response for git ref {context} was not an object.",
            )
        object_payload = payload.get("object")
        if not isinstance(object_payload, dict):
            raise RuntimeError(
                f"GitHub git ref payload for {context} did not contain an object entry.",
            )
        return LiveHostedGitRef(
            ref=str(payload.get("ref", "")).strip(),
            sha=str(object_payload.get("sha", "")).strip(),
        )

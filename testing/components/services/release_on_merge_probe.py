from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any

from testing.core.config.release_on_merge_config import ReleaseOnMergeConfig
from testing.core.interfaces.github_api_client import (
    GitHubApiClient,
    GitHubApiClientError,
)
from testing.core.interfaces.release_on_merge_probe import ReleaseOnMergeObservation
from testing.core.interfaces.url_text_reader import UrlTextReader, UrlTextReaderError


class ReleaseOnMergeProbeError(RuntimeError):
    pass


class ReleaseOnMergeProbeService:
    def __init__(
        self,
        config: ReleaseOnMergeConfig,
        *,
        github_api_client: GitHubApiClient,
        url_text_reader: UrlTextReader,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client
        self._url_text_reader = url_text_reader
        self._tag_pattern = re.compile(self._config.semver_tag_pattern)

    def validate(self) -> ReleaseOnMergeObservation:
        repository_info = self._read_json_object(f"/repos/{self._config.repository}")
        default_branch = self._optional_string(repository_info.get("default_branch"))
        if default_branch is None:
            default_branch = self._config.default_branch

        releases_before = self._list_releases()
        tags_before = self._list_tags()
        release_ids_before = {
            release_id
            for release_id in (self._release_id(entry) for entry in releases_before)
            if release_id is not None
        }
        tag_names_before = {
            tag_name
            for tag_name in (self._optional_string(entry.get("name")) for entry in tags_before)
            if tag_name is not None
        }

        merged_pull_request = self._create_and_merge_pull_request(default_branch)
        pull_request_number = int(merged_pull_request["number"])
        pull_request_url = str(merged_pull_request["url"])
        pull_request_head_branch = str(merged_pull_request["head_branch"])
        pull_request_merged_at = str(merged_pull_request["merged_at"])
        pull_request_merge_commit_sha = str(merged_pull_request["merge_commit_sha"])

        (
            release_entry,
            tag_entry,
            poll_attempts,
        ) = self._wait_for_release_and_tag(
            release_ids_before=release_ids_before,
            tag_names_before=tag_names_before,
            expected_merge_commit_sha=pull_request_merge_commit_sha,
        )

        release_tag_name = self._require_string(release_entry, "tag_name")
        tag_name = self._require_string(tag_entry, "name")
        if release_tag_name != tag_name:
            raise ReleaseOnMergeProbeError(
                "TS-230 observed a new release and a new semantic tag, but they do not "
                f"match.\nRelease tag: {release_tag_name}\nTag name: {tag_name}"
            )

        release_id = self._release_id(release_entry)
        if release_id is None:
            raise ReleaseOnMergeProbeError(
                "TS-230 expected a numeric release id for the observed release entry."
            )

        releases_page_html = self._read_url(self._config.releases_page_url)
        tags_page_html = self._read_url(self._config.tags_page_url)

        return ReleaseOnMergeObservation(
            repository=self._config.repository,
            default_branch=default_branch,
            pull_request_number=pull_request_number,
            pull_request_url=pull_request_url,
            pull_request_head_branch=pull_request_head_branch,
            pull_request_merged_at=pull_request_merged_at,
            pull_request_merge_commit_sha=pull_request_merge_commit_sha,
            release_id=release_id,
            release_tag_name=release_tag_name,
            release_html_url=str(release_entry.get("html_url", "")),
            release_published_at=self._optional_string(release_entry.get("published_at")),
            release_is_draft=self._is_true(release_entry.get("draft")),
            release_is_prerelease=self._is_true(release_entry.get("prerelease")),
            tag_name=tag_name,
            tag_commit_sha=self._optional_string((tag_entry.get("commit") or {}).get("sha")),
            releases_page_url=self._config.releases_page_url,
            tags_page_url=self._config.tags_page_url,
            releases_page_contains_tag=release_tag_name in releases_page_html,
            tags_page_contains_tag=tag_name in tags_page_html,
            poll_attempts=poll_attempts,
        )

    def _create_and_merge_pull_request(self, default_branch: str) -> dict[str, object]:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts230-"))
        branch_name = self._unique_branch_name()
        pull_request_number: int | None = None
        pull_request_url = ""
        branch_pushed = False

        try:
            self._run_command(["gh", "auth", "setup-git"], cwd=None)
            self._run_command(
                [
                    "git",
                    "clone",
                    "--quiet",
                    self._origin_clone_url(),
                    str(temp_repository_root),
                ],
                cwd=None,
            )
            self._run_command(
                ["git", "checkout", "-b", branch_name, f"origin/{default_branch}"],
                cwd=temp_repository_root,
            )
            self._run_command(
                ["git", "config", "user.name", "ai-teammate"],
                cwd=temp_repository_root,
            )
            self._run_command(
                ["git", "config", "user.email", "agent.ai.native@gmail.com"],
                cwd=temp_repository_root,
            )

            probe_file = temp_repository_root / self._config.probe_file_path
            if not probe_file.exists():
                raise ReleaseOnMergeProbeError(
                    "TS-230 precondition failed: probe file path does not exist in the "
                    f"target repository.\nRepository: {self._config.repository}\n"
                    f"Path: {self._config.probe_file_path}"
                )
            marker = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
            with probe_file.open("a", encoding="utf-8") as stream:
                stream.write(f"\n<!-- TS-230 probe {marker} -->\n")

            self._run_command(
                ["git", "add", self._config.probe_file_path],
                cwd=temp_repository_root,
            )
            self._run_command(
                [
                    "git",
                    "commit",
                    "-m",
                    "TS-230 probe: verify release and semantic tag on merge",
                ],
                cwd=temp_repository_root,
            )
            self._run_command(
                ["git", "push", "--set-upstream", "origin", branch_name],
                cwd=temp_repository_root,
            )
            branch_pushed = True

            pull_request_url = self._run_command(
                [
                    "gh",
                    "pr",
                    "create",
                    "--repo",
                    self._config.repository,
                    "--base",
                    default_branch,
                    "--head",
                    branch_name,
                    "--title",
                    self._config.pull_request_title,
                    "--body",
                    self._config.pull_request_body,
                ],
                cwd=temp_repository_root,
            ).stdout.strip()
            pull_request_number = self._extract_pull_request_number(pull_request_url)

            self._run_command(
                [
                    "gh",
                    "pr",
                    "merge",
                    str(pull_request_number),
                    "--repo",
                    self._config.repository,
                    "--squash",
                    "--delete-branch",
                    "--admin",
                ],
                cwd=temp_repository_root,
            )

            merged_pull_request = self._wait_for_merged_pull_request(pull_request_number)
            return {
                "number": pull_request_number,
                "url": pull_request_url,
                "head_branch": branch_name,
                "merged_at": merged_pull_request["merged_at"],
                "merge_commit_sha": merged_pull_request["merge_commit_sha"],
            }
        finally:
            if pull_request_number is not None:
                try:
                    self._close_pull_request_if_open(pull_request_number)
                except ReleaseOnMergeProbeError:
                    pass
            if branch_pushed:
                try:
                    self._delete_branch_if_exists(branch_name)
                except ReleaseOnMergeProbeError:
                    pass
            if temp_repository_root.exists():
                shutil.rmtree(temp_repository_root)

    def _wait_for_merged_pull_request(self, pull_request_number: int) -> dict[str, str]:
        deadline = time.time() + self._config.pull_request_timeout_seconds
        latest_payload: dict[str, Any] | None = None
        while time.time() < deadline:
            latest_payload = self._read_json_object(
                f"/repos/{self._config.repository}/pulls/{pull_request_number}"
            )
            merged_at = self._optional_string(latest_payload.get("merged_at"))
            merge_commit_sha = self._optional_string(latest_payload.get("merge_commit_sha"))
            state = self._optional_string(latest_payload.get("state"))
            if merged_at and merge_commit_sha:
                return {"merged_at": merged_at, "merge_commit_sha": merge_commit_sha}
            if state == "closed" and not merged_at:
                raise ReleaseOnMergeProbeError(
                    f"TS-230 could not verify merge for pull request #{pull_request_number}: "
                    "GitHub reports the pull request is closed without merge metadata.\n"
                    f"Payload: {latest_payload}"
                )
            time.sleep(self._config.poll_interval_seconds)

        raise ReleaseOnMergeProbeError(
            "TS-230 timed out while waiting for merged pull request metadata.\n"
            f"Pull request: #{pull_request_number}\n"
            f"Timeout: {self._config.pull_request_timeout_seconds}s\n"
            f"Last observed payload: {latest_payload}"
        )

    def _wait_for_release_and_tag(
        self,
        *,
        release_ids_before: set[int],
        tag_names_before: set[str],
        expected_merge_commit_sha: str,
    ) -> tuple[dict[str, Any], dict[str, Any], int]:
        deadline = time.time() + self._config.release_timeout_seconds
        attempts = 0
        latest_releases: list[dict[str, Any]] = []
        latest_tags: list[dict[str, Any]] = []
        while time.time() < deadline:
            attempts += 1
            latest_releases = self._list_releases()
            latest_tags = self._list_tags()

            new_semantic_tags = [
                tag
                for tag in latest_tags
                if self._is_new_semantic_tag(tag, tag_names_before)
            ]
            semantic_tag_by_name = {
                tag_name: tag
                for tag in new_semantic_tags
                if (tag_name := self._optional_string(tag.get("name"))) is not None
            }
            for release in latest_releases:
                if self._release_id(release) in release_ids_before:
                    continue
                if self._is_true(release.get("draft")) or self._is_true(
                    release.get("prerelease")
                ):
                    continue
                release_tag_name = self._optional_string(release.get("tag_name"))
                if release_tag_name is None:
                    continue
                matching_tag = semantic_tag_by_name.get(release_tag_name)
                if matching_tag is None:
                    continue
                tag_commit_sha = self._optional_string(
                    (matching_tag.get("commit") or {}).get("sha")
                )
                if tag_commit_sha != expected_merge_commit_sha:
                    continue
                return release, matching_tag, attempts
            time.sleep(self._config.poll_interval_seconds)

        raise ReleaseOnMergeProbeError(
            "TS-230 did not observe both a new GitHub release and a corresponding "
            "new semantic version tag tied to the merged pull request commit, with "
            "the release published as stable (not draft, not prerelease), within the "
            "configured timeout.\n"
            f"Repository: {self._config.repository}\n"
            f"Timeout: {self._config.release_timeout_seconds}s\n"
            f"Expected merge commit sha: {expected_merge_commit_sha}\n"
            f"Baseline release ids: {sorted(release_ids_before)}\n"
            f"Baseline tag names sample: {sorted(tag_names_before)[:20]}\n"
            f"Last observed releases: {latest_releases}\n"
            f"Last observed tags: {latest_tags}"
        )

    def _list_releases(self) -> list[dict[str, Any]]:
        payload = self._read_json(
            f"/repos/{self._config.repository}/releases?per_page={self._config.releases_lookup_limit}"
        )
        if not isinstance(payload, list):
            raise ReleaseOnMergeProbeError(
                "TS-230 expected GitHub releases API to return a list."
            )
        return [entry for entry in payload if isinstance(entry, dict)]

    def _list_tags(self) -> list[dict[str, Any]]:
        payload = self._read_json(
            f"/repos/{self._config.repository}/tags?per_page={self._config.tags_lookup_limit}"
        )
        if not isinstance(payload, list):
            raise ReleaseOnMergeProbeError("TS-230 expected GitHub tags API to return a list.")
        return [entry for entry in payload if isinstance(entry, dict)]

    def _close_pull_request_if_open(self, pull_request_number: int) -> None:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/pulls/{pull_request_number}"
        )
        state = self._optional_string(payload.get("state"))
        if state != "open":
            return
        self._read_json_object(
            f"/repos/{self._config.repository}/pulls/{pull_request_number}",
            method="PATCH",
            field_args=["-f", "state=closed"],
        )

    def _delete_branch_if_exists(self, branch_name: str) -> None:
        self._run_command(["git", "push", "origin", "--delete", branch_name], cwd=None)

    def _read_url(self, url: str) -> str:
        try:
            return self._url_text_reader.read_text(
                url=url,
                headers={"Accept": "text/html"},
                timeout_seconds=60,
            )
        except UrlTextReaderError as error:
            raise ReleaseOnMergeProbeError(str(error)) from error

    def _origin_clone_url(self) -> str:
        return f"https://github.com/{self._config.repository}.git"

    def _run_command(
        self,
        command: list[str],
        *,
        cwd: Path | None,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment.setdefault("GH_PAGER", "cat")
        environment.setdefault("GIT_TERMINAL_PROMPT", "0")
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            command_text = " ".join(command)
            raise ReleaseOnMergeProbeError(
                f"{command_text} failed with exit code {completed.returncode}.\n"
                f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        return completed

    def _read_json_object(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        field_args: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = self._read_json(endpoint, method=method, field_args=field_args)
        if not isinstance(payload, dict):
            raise ReleaseOnMergeProbeError(
                f"Expected a JSON object from gh api {endpoint}, got {type(payload)}."
            )
        return payload

    def _read_json(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        field_args: list[str] | None = None,
    ) -> object:
        try:
            response_text = self._github_api_client.request_text(
                endpoint=endpoint,
                method=method,
                field_args=field_args,
            )
        except GitHubApiClientError as error:
            raise ReleaseOnMergeProbeError(str(error)) from error
        return json.loads(response_text)

    def _extract_pull_request_number(self, pull_request_url: str) -> int:
        match = re.search(r"/pull/(\d+)$", pull_request_url.strip())
        if match is None:
            raise ReleaseOnMergeProbeError(
                "gh pr create did not return a pull request URL ending in /pull/<number>: "
                f"{pull_request_url}"
            )
        return int(match.group(1))

    def _unique_branch_name(self) -> str:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"{self._config.branch_prefix}-{timestamp}"

    def _is_new_semantic_tag(
        self,
        tag: dict[str, Any],
        baseline_tag_names: set[str],
    ) -> bool:
        name = self._optional_string(tag.get("name"))
        if name is None:
            return False
        if name in baseline_tag_names:
            return False
        return self._tag_pattern.fullmatch(name) is not None

    @staticmethod
    def _release_id(release_entry: dict[str, Any]) -> int | None:
        release_id = release_entry.get("id")
        if isinstance(release_id, int):
            return release_id
        return None

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _is_true(value: object) -> bool:
        return value is True

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str) -> str:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        raise ReleaseOnMergeProbeError(
            f"TS-230 expected {key} to be a non-empty string in payload: {payload}"
        )

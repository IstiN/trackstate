from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from typing import Any

from testing.core.config.non_default_branch_release_config import (
    NonDefaultBranchReleaseConfig,
)
from testing.core.interfaces.github_api_client import (
    GitHubApiClient,
    GitHubApiClientError,
)
from testing.core.interfaces.non_default_branch_release_probe import (
    NonDefaultBranchReleaseObservation,
)
from testing.core.interfaces.url_text_reader import UrlTextReader, UrlTextReaderError


class NonDefaultBranchReleaseProbeError(RuntimeError):
    pass


class NonDefaultBranchReleaseProbeService:
    def __init__(
        self,
        config: NonDefaultBranchReleaseConfig,
        *,
        github_api_client: GitHubApiClient,
        url_text_reader: UrlTextReader,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client
        self._url_text_reader = url_text_reader
        self._tag_pattern = re.compile(self._config.semver_tag_pattern)

    def validate(self) -> NonDefaultBranchReleaseObservation:
        repository_info = self._read_json_object(f"/repos/{self._config.repository}")
        default_branch = self._optional_string(repository_info.get("default_branch"))
        if default_branch is None:
            default_branch = self._config.default_branch

        releases_before = self._list_releases()
        tags_before = self._list_tags()
        baseline_release_ids = sorted(
            release_id
            for release_id in (self._release_id(entry) for entry in releases_before)
            if release_id is not None
        )
        baseline_semver_tag_names = sorted(
            tag_name
            for tag_name in (
                self._optional_string(entry.get("name")) for entry in tags_before
            )
            if tag_name is not None and self._tag_pattern.fullmatch(tag_name) is not None
        )

        merged_pull_request = self._create_and_merge_pull_request(default_branch)
        try:
            (
                unexpected_release_entry,
                unexpected_tag_entry,
                poll_attempts,
                elapsed_quiet_period_seconds,
                observed_new_release_ids,
                observed_new_semver_tag_names,
            ) = self._wait_for_no_release_or_tag_for_merge_commit(
                baseline_release_ids=set(baseline_release_ids),
                baseline_semver_tag_names=set(baseline_semver_tag_names),
                expected_merge_commit_sha=merged_pull_request["merge_commit_sha"],
            )

            releases_page_html = self._read_url(self._config.releases_page_url)
            tags_page_html = self._read_url(self._config.tags_page_url)
        finally:
            self._cleanup_disposable_environment(merged_pull_request)

        unexpected_release_tag_name = None
        unexpected_release_html_url = None
        unexpected_release_id = None
        unexpected_release_tag_commit_sha = None
        if unexpected_release_entry is not None:
            unexpected_release_tag_name = self._optional_string(
                unexpected_release_entry.get("tag_name")
            )
            unexpected_release_html_url = self._optional_string(
                unexpected_release_entry.get("html_url")
            )
            unexpected_release_id = self._release_id(unexpected_release_entry)
            unexpected_release_tag_commit_sha = self._resolve_tag_commit_sha(
                unexpected_release_tag_name,
                unexpected_tag_entry,
            )

        unexpected_tag_name = None
        unexpected_tag_commit_sha = None
        if unexpected_tag_entry is not None:
            unexpected_tag_name = self._optional_string(unexpected_tag_entry.get("name"))
            unexpected_tag_commit_sha = self._optional_string(
                (unexpected_tag_entry.get("commit") or {}).get("sha")
            )

        visible_unexpected_tag = unexpected_tag_name or unexpected_release_tag_name

        return NonDefaultBranchReleaseObservation(
            repository=self._config.repository,
            default_branch=default_branch,
            target_branch=merged_pull_request["base_branch"],
            target_branch_created_by_test=bool(
                merged_pull_request["target_branch_created_by_test"]
            ),
            pull_request_number=int(merged_pull_request["number"]),
            pull_request_url=merged_pull_request["url"],
            pull_request_head_branch=merged_pull_request["head_branch"],
            pull_request_base_branch=merged_pull_request["base_branch"],
            pull_request_merged_at=merged_pull_request["merged_at"],
            pull_request_merge_commit_sha=merged_pull_request["merge_commit_sha"],
            releases_page_url=self._config.releases_page_url,
            tags_page_url=self._config.tags_page_url,
            releases_page_has_heading="Releases" in releases_page_html,
            tags_page_has_heading="Tags" in tags_page_html,
            releases_page_contains_unexpected_tag=bool(
                visible_unexpected_tag and visible_unexpected_tag in releases_page_html
            ),
            tags_page_contains_unexpected_tag=bool(
                visible_unexpected_tag and visible_unexpected_tag in tags_page_html
            ),
            unexpected_release_id=unexpected_release_id,
            unexpected_release_tag_name=unexpected_release_tag_name,
            unexpected_release_html_url=unexpected_release_html_url,
            unexpected_release_tag_commit_sha=unexpected_release_tag_commit_sha,
            unexpected_tag_name=unexpected_tag_name,
            unexpected_tag_commit_sha=unexpected_tag_commit_sha,
            baseline_release_ids=baseline_release_ids,
            baseline_semver_tag_names=baseline_semver_tag_names,
            observed_new_release_ids=observed_new_release_ids,
            observed_new_semver_tag_names=observed_new_semver_tag_names,
            poll_attempts=poll_attempts,
            quiet_period_seconds=self._config.quiet_period_seconds,
            elapsed_quiet_period_seconds=elapsed_quiet_period_seconds,
        )

    def _create_and_merge_pull_request(self, default_branch: str) -> dict[str, object]:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts252-"))
        target_branch_name, source_branch_name = self._unique_branch_names()
        pull_request_number: int | None = None
        pull_request_url = ""
        source_branch_pushed = False
        target_branch_pushed = False
        disposable_environment: dict[str, object] | None = None

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
                ["git", "checkout", "-b", target_branch_name, f"origin/{default_branch}"],
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
            self._run_command(
                ["git", "push", "--set-upstream", "origin", target_branch_name],
                cwd=temp_repository_root,
            )
            target_branch_pushed = True

            self._run_command(
                ["git", "checkout", "-b", source_branch_name, target_branch_name],
                cwd=temp_repository_root,
            )

            probe_file = temp_repository_root / self._config.probe_file_path
            if not probe_file.exists():
                raise NonDefaultBranchReleaseProbeError(
                    "TS-252 precondition failed: probe file path does not exist in the "
                    f"target repository.\nRepository: {self._config.repository}\n"
                    f"Path: {self._config.probe_file_path}"
                )
            marker = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
            with probe_file.open("a", encoding="utf-8") as stream:
                stream.write(f"\n<!-- TS-252 probe {marker} -->\n")

            self._run_command(
                ["git", "add", self._config.probe_file_path],
                cwd=temp_repository_root,
            )
            self._run_command(
                [
                    "git",
                    "commit",
                    "-m",
                    "TS-252 probe: verify non-default branch merge does not release",
                ],
                cwd=temp_repository_root,
            )
            self._run_command(
                ["git", "push", "--set-upstream", "origin", source_branch_name],
                cwd=temp_repository_root,
            )
            source_branch_pushed = True

            pull_request_url = self._run_command(
                [
                    "gh",
                    "pr",
                    "create",
                    "--repo",
                    self._config.repository,
                    "--base",
                    target_branch_name,
                    "--head",
                    source_branch_name,
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
            disposable_environment = {
                "number": pull_request_number,
                "url": pull_request_url,
                "head_branch": source_branch_name,
                "base_branch": merged_pull_request["base_ref"],
                "merged_at": merged_pull_request["merged_at"],
                "merge_commit_sha": merged_pull_request["merge_commit_sha"],
                "target_branch_created_by_test": True,
                "temp_repository_root": temp_repository_root,
                "source_branch_pushed": source_branch_pushed,
                "target_branch_pushed": target_branch_pushed,
            }
            return disposable_environment
        finally:
            if disposable_environment is None and temp_repository_root.exists():
                if pull_request_number is not None:
                    try:
                        self._close_pull_request_if_open(pull_request_number)
                    except NonDefaultBranchReleaseProbeError:
                        pass
                if source_branch_pushed:
                    try:
                        self._delete_branch_if_exists(
                            source_branch_name,
                            cwd=temp_repository_root,
                        )
                    except NonDefaultBranchReleaseProbeError:
                        pass
                if target_branch_pushed:
                    try:
                        self._delete_branch_if_exists(
                            target_branch_name,
                            cwd=temp_repository_root,
                        )
                    except NonDefaultBranchReleaseProbeError:
                        pass
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
            base_ref = self._optional_string((latest_payload.get("base") or {}).get("ref"))
            if merged_at and merge_commit_sha and base_ref:
                return {
                    "merged_at": merged_at,
                    "merge_commit_sha": merge_commit_sha,
                    "base_ref": base_ref,
                }
            if state == "closed" and not merged_at:
                raise NonDefaultBranchReleaseProbeError(
                    f"TS-252 could not verify merge for pull request #{pull_request_number}: "
                    "GitHub reports the pull request is closed without merge metadata.\n"
                    f"Payload: {latest_payload}"
                )
            time.sleep(self._config.poll_interval_seconds)

        raise NonDefaultBranchReleaseProbeError(
            "TS-252 timed out while waiting for merged pull request metadata.\n"
            f"Pull request: #{pull_request_number}\n"
            f"Timeout: {self._config.pull_request_timeout_seconds}s\n"
            f"Last observed payload: {latest_payload}"
        )

    def _wait_for_no_release_or_tag_for_merge_commit(
        self,
        *,
        baseline_release_ids: set[int],
        baseline_semver_tag_names: set[str],
        expected_merge_commit_sha: str,
    ) -> tuple[
        dict[str, Any] | None,
        dict[str, Any] | None,
        int,
        int,
        list[int],
        list[str],
    ]:
        deadline = time.time() + self._config.quiet_period_seconds
        started_at = time.time()
        attempts = 0
        observed_new_release_ids: set[int] = set()
        observed_new_semver_tag_names: set[str] = set()

        while True:
            attempts += 1
            latest_releases = self._list_releases()
            latest_tags = self._list_tags()

            unexpected_release_entry, unexpected_tag_entry = self._find_unexpected_release_or_tag(
                releases=latest_releases,
                tags=latest_tags,
                baseline_release_ids=baseline_release_ids,
                baseline_semver_tag_names=baseline_semver_tag_names,
                expected_merge_commit_sha=expected_merge_commit_sha,
                observed_new_release_ids=observed_new_release_ids,
                observed_new_semver_tag_names=observed_new_semver_tag_names,
            )
            elapsed_quiet_period_seconds = math.ceil(time.time() - started_at)
            if unexpected_release_entry is not None or unexpected_tag_entry is not None:
                return (
                    unexpected_release_entry,
                    unexpected_tag_entry,
                    attempts,
                    elapsed_quiet_period_seconds,
                    sorted(observed_new_release_ids),
                    sorted(observed_new_semver_tag_names),
                )
            if time.time() >= deadline:
                return (
                    None,
                    None,
                    attempts,
                    elapsed_quiet_period_seconds,
                    sorted(observed_new_release_ids),
                    sorted(observed_new_semver_tag_names),
                )
            time.sleep(self._config.poll_interval_seconds)

    def _cleanup_disposable_environment(
        self,
        disposable_environment: dict[str, object],
    ) -> None:
        temp_repository_root = Path(str(disposable_environment["temp_repository_root"]))
        pull_request_number = int(disposable_environment["number"])
        source_branch_name = str(disposable_environment["head_branch"])
        target_branch_name = str(disposable_environment["base_branch"])
        source_branch_pushed = bool(disposable_environment["source_branch_pushed"])
        target_branch_pushed = bool(disposable_environment["target_branch_pushed"])

        if temp_repository_root.exists():
            try:
                self._close_pull_request_if_open(pull_request_number)
            except NonDefaultBranchReleaseProbeError:
                pass
            if source_branch_pushed:
                try:
                    self._delete_branch_if_exists(source_branch_name, cwd=temp_repository_root)
                except NonDefaultBranchReleaseProbeError:
                    pass
            if target_branch_pushed:
                try:
                    self._delete_branch_if_exists(target_branch_name, cwd=temp_repository_root)
                except NonDefaultBranchReleaseProbeError:
                    pass
            shutil.rmtree(temp_repository_root)

    def _find_unexpected_release_or_tag(
        self,
        *,
        releases: list[dict[str, Any]],
        tags: list[dict[str, Any]],
        baseline_release_ids: set[int],
        baseline_semver_tag_names: set[str],
        expected_merge_commit_sha: str,
        observed_new_release_ids: set[int],
        observed_new_semver_tag_names: set[str],
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        tag_by_name: dict[str, dict[str, Any]] = {}
        for tag in tags:
            tag_name = self._optional_string(tag.get("name"))
            if tag_name is None:
                continue
            tag_by_name[tag_name] = tag
            if tag_name in baseline_semver_tag_names:
                continue
            if self._tag_pattern.fullmatch(tag_name) is None:
                continue
            observed_new_semver_tag_names.add(tag_name)
            tag_commit_sha = self._optional_string((tag.get("commit") or {}).get("sha"))
            if tag_commit_sha == expected_merge_commit_sha:
                return None, tag

        for release in releases:
            release_id = self._release_id(release)
            if release_id is None or release_id in baseline_release_ids:
                continue
            if self._is_true(release.get("draft")) or self._is_true(
                release.get("prerelease")
            ):
                continue
            observed_new_release_ids.add(release_id)
            release_tag_name = self._optional_string(release.get("tag_name"))
            if release_tag_name is None:
                continue
            matching_tag = tag_by_name.get(release_tag_name)
            tag_commit_sha = self._resolve_tag_commit_sha(release_tag_name, matching_tag)
            if tag_commit_sha == expected_merge_commit_sha:
                return release, matching_tag

        return None, None

    def _list_releases(self) -> list[dict[str, Any]]:
        payload = self._read_json(
            f"/repos/{self._config.repository}/releases?per_page={self._config.releases_lookup_limit}"
        )
        if not isinstance(payload, list):
            raise NonDefaultBranchReleaseProbeError(
                "TS-252 expected GitHub releases API to return a list."
            )
        return [entry for entry in payload if isinstance(entry, dict)]

    def _list_tags(self) -> list[dict[str, Any]]:
        payload = self._read_json(
            f"/repos/{self._config.repository}/tags?per_page={self._config.tags_lookup_limit}"
        )
        if not isinstance(payload, list):
            raise NonDefaultBranchReleaseProbeError(
                "TS-252 expected GitHub tags API to return a list."
            )
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

    def _delete_branch_if_exists(self, branch_name: str, *, cwd: Path) -> None:
        if not self._branch_exists_on_origin(branch_name, cwd=cwd):
            return
        self._run_command(["git", "push", "origin", "--delete", branch_name], cwd=cwd)

    def _branch_exists_on_origin(self, branch_name: str, *, cwd: Path) -> bool:
        completed = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", branch_name],
            cwd=cwd,
            env=self._command_environment(),
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise NonDefaultBranchReleaseProbeError(
                "git ls-remote failed while checking disposable branch cleanup.\n"
                f"Branch: {branch_name}\n"
                f"STDOUT:\n{completed.stdout}\n"
                f"STDERR:\n{completed.stderr}"
            )
        return bool(completed.stdout.strip())

    def _resolve_tag_commit_sha(
        self,
        tag_name: str | None,
        tag_entry: dict[str, Any] | None,
    ) -> str | None:
        if tag_entry is not None:
            return self._optional_string((tag_entry.get("commit") or {}).get("sha"))
        if tag_name is None:
            return None
        latest_tags = self._list_tags()
        for candidate in latest_tags:
            candidate_name = self._optional_string(candidate.get("name"))
            if candidate_name != tag_name:
                continue
            return self._optional_string((candidate.get("commit") or {}).get("sha"))
        return None

    def _read_url(self, url: str) -> str:
        try:
            return self._url_text_reader.read_text(
                url=url,
                headers={"Accept": "text/html"},
                timeout_seconds=60,
            )
        except UrlTextReaderError as error:
            raise NonDefaultBranchReleaseProbeError(str(error)) from error

    def _origin_clone_url(self) -> str:
        return f"https://github.com/{self._config.repository}.git"

    def _run_command(
        self,
        command: list[str],
        *,
        cwd: Path | None,
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=self._command_environment(),
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            command_text = " ".join(command)
            raise NonDefaultBranchReleaseProbeError(
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
            raise NonDefaultBranchReleaseProbeError(
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
            raise NonDefaultBranchReleaseProbeError(str(error)) from error
        return json.loads(response_text)

    def _extract_pull_request_number(self, pull_request_url: str) -> int:
        match = re.search(r"/pull/(\d+)$", pull_request_url.strip())
        if match is None:
            raise NonDefaultBranchReleaseProbeError(
                "gh pr create did not return a pull request URL ending in /pull/<number>: "
                f"{pull_request_url}"
            )
        return int(match.group(1))

    def _unique_branch_names(self) -> tuple[str, str]:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S")
        return (
            f"{self._config.branch_prefix}-base-{timestamp}",
            f"{self._config.branch_prefix}-pr-{timestamp}",
        )

    @staticmethod
    def _command_environment() -> dict[str, str]:
        environment = os.environ.copy()
        environment.setdefault("GH_PAGER", "cat")
        environment.setdefault("GIT_TERMINAL_PROMPT", "0")
        return environment

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

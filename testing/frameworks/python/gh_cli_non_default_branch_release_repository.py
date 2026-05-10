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

from testing.core.config.non_default_branch_release_config import (
    NonDefaultBranchReleaseConfig,
)
from testing.core.interfaces.github_api_client import (
    GitHubApiClient,
    GitHubApiClientError,
)
from testing.core.interfaces.non_default_branch_release_repository import (
    NonDefaultBranchMergedPullRequest,
    NonDefaultBranchReleaseRepository,
    NonDefaultBranchReleaseRepositoryError,
)


class GhCliNonDefaultBranchReleaseRepository(NonDefaultBranchReleaseRepository):
    def __init__(
        self,
        repository_root: Path,
        *,
        github_api_client: GitHubApiClient,
    ) -> None:
        self._repository_root = Path(repository_root)
        self._github_api_client = github_api_client

    def create_and_merge_pull_request(
        self,
        *,
        config: NonDefaultBranchReleaseConfig,
        default_branch: str,
    ) -> NonDefaultBranchMergedPullRequest:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts252-"))
        target_branch_name, source_branch_name = self._unique_branch_names(config)
        pull_request_number: int | None = None
        pull_request_url = ""
        source_branch_pushed = False
        target_branch_pushed = False
        merged_pull_request: NonDefaultBranchMergedPullRequest | None = None

        try:
            self._run_command(["gh", "auth", "setup-git"], cwd=None)
            self._run_command(
                [
                    "git",
                    "clone",
                    "--quiet",
                    self._origin_clone_url(config),
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

            probe_file = temp_repository_root / config.probe_file_path
            if not probe_file.exists():
                raise NonDefaultBranchReleaseRepositoryError(
                    "TS-252 precondition failed: probe file path does not exist in the "
                    f"target repository.\nRepository: {config.repository}\n"
                    f"Path: {config.probe_file_path}"
                )
            marker = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
            with probe_file.open("a", encoding="utf-8") as stream:
                stream.write(f"\n<!-- TS-252 probe {marker} -->\n")

            self._run_command(["git", "add", config.probe_file_path], cwd=temp_repository_root)
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
                    config.repository,
                    "--base",
                    target_branch_name,
                    "--head",
                    source_branch_name,
                    "--title",
                    config.pull_request_title,
                    "--body",
                    config.pull_request_body,
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
                    config.repository,
                    "--squash",
                    "--delete-branch",
                    "--admin",
                ],
                cwd=temp_repository_root,
            )

            merged_metadata = self._wait_for_merged_pull_request(
                config=config,
                pull_request_number=pull_request_number,
            )
            merged_pull_request = NonDefaultBranchMergedPullRequest(
                number=pull_request_number,
                url=pull_request_url,
                head_branch=source_branch_name,
                base_branch=merged_metadata["base_ref"],
                merged_at=merged_metadata["merged_at"],
                merge_commit_sha=merged_metadata["merge_commit_sha"],
                target_branch_created_by_test=True,
                temp_repository_root=temp_repository_root,
                source_branch_pushed=source_branch_pushed,
                target_branch_pushed=target_branch_pushed,
            )
            return merged_pull_request
        finally:
            if merged_pull_request is None and temp_repository_root.exists():
                if pull_request_number is not None:
                    try:
                        self._close_pull_request_if_open(
                            repository=config.repository,
                            pull_request_number=pull_request_number,
                        )
                    except NonDefaultBranchReleaseRepositoryError:
                        pass
                if source_branch_pushed:
                    try:
                        self._delete_branch_if_exists(
                            source_branch_name,
                            cwd=temp_repository_root,
                        )
                    except NonDefaultBranchReleaseRepositoryError:
                        pass
                if target_branch_pushed:
                    try:
                        self._delete_branch_if_exists(
                            target_branch_name,
                            cwd=temp_repository_root,
                        )
                    except NonDefaultBranchReleaseRepositoryError:
                        pass
                shutil.rmtree(temp_repository_root)

    def cleanup_disposable_environment(
        self,
        merged_pull_request: NonDefaultBranchMergedPullRequest,
    ) -> None:
        temp_repository_root = merged_pull_request.temp_repository_root
        if not temp_repository_root.exists():
            return

        try:
            self._close_pull_request_if_open(
                repository=self._repository_from_pull_request_url(merged_pull_request.url),
                pull_request_number=merged_pull_request.number,
            )
        except NonDefaultBranchReleaseRepositoryError:
            pass
        if merged_pull_request.source_branch_pushed:
            try:
                self._delete_branch_if_exists(
                    merged_pull_request.head_branch,
                    cwd=temp_repository_root,
                )
            except NonDefaultBranchReleaseRepositoryError:
                pass
        if merged_pull_request.target_branch_pushed:
            try:
                self._delete_branch_if_exists(
                    merged_pull_request.base_branch,
                    cwd=temp_repository_root,
                )
            except NonDefaultBranchReleaseRepositoryError:
                pass
        shutil.rmtree(temp_repository_root)

    def _wait_for_merged_pull_request(
        self,
        *,
        config: NonDefaultBranchReleaseConfig,
        pull_request_number: int,
    ) -> dict[str, str]:
        deadline = time.time() + config.pull_request_timeout_seconds
        latest_payload: dict[str, Any] | None = None
        while time.time() < deadline:
            latest_payload = self._read_json_object(
                f"/repos/{config.repository}/pulls/{pull_request_number}"
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
                raise NonDefaultBranchReleaseRepositoryError(
                    f"TS-252 could not verify merge for pull request #{pull_request_number}: "
                    "GitHub reports the pull request is closed without merge metadata.\n"
                    f"Payload: {latest_payload}"
                )
            time.sleep(config.poll_interval_seconds)

        raise NonDefaultBranchReleaseRepositoryError(
            "TS-252 timed out while waiting for merged pull request metadata.\n"
            f"Pull request: #{pull_request_number}\n"
            f"Timeout: {config.pull_request_timeout_seconds}s\n"
            f"Last observed payload: {latest_payload}"
        )

    def _close_pull_request_if_open(
        self,
        *,
        repository: str,
        pull_request_number: int,
    ) -> None:
        payload = self._read_json_object(f"/repos/{repository}/pulls/{pull_request_number}")
        state = self._optional_string(payload.get("state"))
        if state != "open":
            return
        self._read_json_object(
            f"/repos/{repository}/pulls/{pull_request_number}",
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
            raise NonDefaultBranchReleaseRepositoryError(
                "git ls-remote failed while checking disposable branch cleanup.\n"
                f"Branch: {branch_name}\n"
                f"STDOUT:\n{completed.stdout}\n"
                f"STDERR:\n{completed.stderr}"
            )
        return bool(completed.stdout.strip())

    def _read_json_object(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        field_args: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = self._read_json(endpoint, method=method, field_args=field_args)
        if not isinstance(payload, dict):
            raise NonDefaultBranchReleaseRepositoryError(
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
            raise NonDefaultBranchReleaseRepositoryError(str(error)) from error
        return json.loads(response_text)

    def _origin_clone_url(self, config: NonDefaultBranchReleaseConfig) -> str:
        return f"https://github.com/{config.repository}.git"

    def _extract_pull_request_number(self, pull_request_url: str) -> int:
        match = re.search(r"/pull/(\d+)$", pull_request_url.strip())
        if match is None:
            raise NonDefaultBranchReleaseRepositoryError(
                "gh pr create did not return a pull request URL ending in /pull/<number>: "
                f"{pull_request_url}"
            )
        return int(match.group(1))

    def _unique_branch_names(
        self,
        config: NonDefaultBranchReleaseConfig,
    ) -> tuple[str, str]:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S")
        return (
            f"{config.branch_prefix}-base-{timestamp}",
            f"{config.branch_prefix}-pr-{timestamp}",
        )

    def _run_command(
        self,
        command: list[str],
        *,
        cwd: Path | None,
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            command,
            cwd=cwd or self._repository_root,
            env=self._command_environment(),
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            command_text = " ".join(command)
            raise NonDefaultBranchReleaseRepositoryError(
                f"{command_text} failed with exit code {completed.returncode}.\n"
                f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
            )
        return completed

    @staticmethod
    def _command_environment() -> dict[str, str]:
        environment = os.environ.copy()
        environment.setdefault("GH_PAGER", "cat")
        environment.setdefault("GIT_TERMINAL_PROMPT", "0")
        return environment

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _repository_from_pull_request_url(pull_request_url: str) -> str:
        match = re.search(r"github\.com/([^/]+/[^/]+)/pull/\d+$", pull_request_url.strip())
        if match is None:
            raise NonDefaultBranchReleaseRepositoryError(
                "TS-252 could not derive the repository from the pull request URL.\n"
                f"Pull request URL: {pull_request_url}"
            )
        return match.group(1)

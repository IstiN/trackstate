from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

from testing.core.config.theme_token_ci_config import ThemeTokenCiConfig
from testing.core.interfaces.github_api_client import (
    GitHubApiClient,
    GitHubApiClientError,
)
from testing.core.interfaces.theme_token_ci_probe import ThemeTokenCiObservation


class ThemeTokenCiError(RuntimeError):
    pass


@dataclass(frozen=True)
class _DisposablePullRequest:
    temp_repository_root: Path
    branch_name: str
    commit_sha: str
    pull_request_number: int
    pull_request_url: str
    pull_request_title: str
    probe_relative_path: str


class ThemeTokenCiWorkflowProbe:
    def __init__(
        self,
        config: ThemeTokenCiConfig,
        *,
        github_api_client: GitHubApiClient,
    ) -> None:
        self._config = config
        self._github_api_client = github_api_client

    def validate(self) -> ThemeTokenCiObservation:
        repository_info = self._read_json_object(f"/repos/{self._config.repository}")
        default_branch = self._default_branch(repository_info)
        workflow = self._select_workflow()
        workflow_id = workflow.get("id")
        if not isinstance(workflow_id, int):
            raise ThemeTokenCiError(
                "TS-131 could not resolve a numeric workflow ID for "
                f"{self._config.workflow_path}."
            )

        workflow_text = self._read_workflow_text(default_branch)
        disposable_pull_request = self._create_disposable_pull_request(default_branch)
        try:
            run, jobs, step, matched_job_name = self._wait_for_pull_request_run(
                workflow_id,
                disposable_pull_request,
            )
            observed_job_names = self._job_names(jobs)
            observed_step_names = self._step_names(jobs)

            return ThemeTokenCiObservation(
                repository=self._config.repository,
                workflow_id=workflow_id,
                workflow_name=str(workflow.get("name", "")),
                workflow_path=self._config.workflow_path,
                workflow_html_url=str(workflow.get("html_url", "")),
                default_branch=default_branch,
                workflow_text=workflow_text,
                pull_request_number=disposable_pull_request.pull_request_number,
                pull_request_url=disposable_pull_request.pull_request_url,
                pull_request_head_branch=disposable_pull_request.branch_name,
                pull_request_head_sha=disposable_pull_request.commit_sha,
                pull_request_title=disposable_pull_request.pull_request_title,
                probe_relative_path=disposable_pull_request.probe_relative_path,
                workflow_run_id=int(run["id"]),
                workflow_run_url=str(run.get("html_url", "")),
                workflow_run_event=str(run.get("event", "")),
                workflow_run_status=self._optional_string(run.get("status")),
                workflow_run_conclusion=self._optional_string(run.get("conclusion")),
                observed_job_names=observed_job_names,
                observed_step_names=observed_step_names,
                theme_token_job_name=matched_job_name,
                theme_token_step_status=self._optional_string(step.get("status"))
                if step
                else None,
                theme_token_step_conclusion=self._optional_string(step.get("conclusion"))
                if step
                else None,
                workflow_declares_pull_request_trigger=bool(
                    re.search(r"(?m)^\s*pull_request:\s*$", workflow_text),
                ),
                workflow_declares_gate_step=(
                    f"- name: {self._config.workflow_step_name}" in workflow_text
                ),
                workflow_declares_gate_command=self._config.gate_command in workflow_text,
            )
        finally:
            self._cleanup_disposable_pull_request(disposable_pull_request)

    def _select_workflow(self) -> dict[str, Any]:
        payload = self._read_json_object(f"/repos/{self._config.repository}/actions/workflows")
        workflows = payload.get("workflows")
        if not isinstance(workflows, list):
            raise ThemeTokenCiError(
                "GitHub Actions workflows response did not return a workflows list."
            )

        for workflow in workflows:
            if not isinstance(workflow, dict):
                continue
            path = workflow.get("path")
            if isinstance(path, str) and path == self._config.workflow_path:
                return workflow

        raise ThemeTokenCiError(
            "TS-131 could not find the configured workflow path "
            f"{self._config.workflow_path} in {self._config.repository}."
        )

    def _read_workflow_text(self, default_branch: str) -> str:
        path = quote(self._config.workflow_path, safe="/")
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/contents/{path}?ref="
            f"{quote(default_branch, safe='')}"
        )
        encoded_content = payload.get("content")
        if not isinstance(encoded_content, str) or not encoded_content.strip():
            raise ThemeTokenCiError(
                "GitHub did not return base64 workflow contents for "
                f"{self._config.workflow_path}."
            )
        return base64.b64decode(encoded_content.replace("\n", "")).decode("utf-8")

    def _wait_for_pull_request_run(
        self,
        workflow_id: int,
        disposable_pull_request: _DisposablePullRequest,
    ) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any] | None, str | None]:
        deadline = time.time() + self._config.run_timeout_seconds
        latest_run_detail: dict[str, Any] | None = None

        while time.time() < deadline:
            run = self._select_matching_pull_request_run(
                workflow_id,
                disposable_pull_request,
            )
            if run is None:
                time.sleep(self._config.poll_interval_seconds)
                continue

            run_id = run.get("id")
            if not isinstance(run_id, int):
                time.sleep(self._config.poll_interval_seconds)
                continue

            latest_run_detail = self._read_json_object(
                f"/repos/{self._config.repository}/actions/runs/{run_id}"
            )
            if latest_run_detail.get("status") != "completed":
                time.sleep(self._config.poll_interval_seconds)
                continue
            if latest_run_detail.get("conclusion") == "cancelled":
                time.sleep(self._config.poll_interval_seconds)
                continue

            jobs = self._read_jobs(run_id)
            step, matched_job_name = self._find_theme_token_step(jobs)
            return latest_run_detail, jobs, step, matched_job_name

        if latest_run_detail is not None:
            raise ThemeTokenCiError(
                "TS-131 created a disposable Pull Request, but the matching "
                "workflow run did not complete in time.\n"
                f"Pull Request: {disposable_pull_request.pull_request_url}\n"
                f"Last observed run: {latest_run_detail.get('html_url')}\n"
                f"Status: {latest_run_detail.get('status')}\n"
                f"Conclusion: {latest_run_detail.get('conclusion')}"
            )
        raise ThemeTokenCiError(
            "TS-131 created a disposable Pull Request, but GitHub Actions never "
            f"started a matching {self._config.workflow_path} run within "
            f"{self._config.run_timeout_seconds} seconds.\n"
            f"Pull Request: {disposable_pull_request.pull_request_url}"
        )

    def _select_matching_pull_request_run(
        self,
        workflow_id: int,
        disposable_pull_request: _DisposablePullRequest,
    ) -> dict[str, Any] | None:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/actions/workflows/{workflow_id}/runs"
            f"?event=pull_request&per_page={self._config.recent_run_limit}"
        )
        workflow_runs = payload.get("workflow_runs")
        if not isinstance(workflow_runs, list):
            raise ThemeTokenCiError(
                "GitHub Actions runs response did not return a workflow_runs list."
            )

        matches: list[dict[str, Any]] = []
        for run in workflow_runs:
            if not isinstance(run, dict):
                continue
            if str(run.get("head_branch", "")).strip() != disposable_pull_request.branch_name:
                continue
            head_sha = str(run.get("head_sha", "")).strip()
            if head_sha and head_sha != disposable_pull_request.commit_sha:
                continue
            matches.append(run)

        if not matches:
            return None
        return max(
            matches,
            key=lambda run: (
                self._run_created_at_epoch(run) or 0.0,
                int(run.get("id", 0)),
            ),
        )

    def _read_jobs(self, run_id: int) -> list[dict[str, Any]]:
        payload = self._read_json_object(
            f"/repos/{self._config.repository}/actions/runs/{run_id}/jobs?per_page=20"
        )
        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise ThemeTokenCiError(
                f"GitHub Actions jobs response for run {run_id} did not return a list."
            )
        return [job for job in jobs if isinstance(job, dict)]

    def _find_theme_token_step(
        self,
        jobs: list[dict[str, Any]],
    ) -> tuple[dict[str, Any] | None, str | None]:
        preferred_jobs = [
            job
            for job in jobs
            if str(job.get("name", "")).strip() == self._config.workflow_job_name
        ]
        jobs_to_search = preferred_jobs or jobs

        for job in jobs_to_search:
            steps = job.get("steps")
            if not isinstance(steps, list):
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                if str(step.get("name", "")).strip() == self._config.workflow_step_name:
                    return step, self._optional_string(job.get("name"))
        return None, None

    @staticmethod
    def _default_branch(repository_info: dict[str, Any]) -> str:
        default_branch = repository_info.get("default_branch")
        if isinstance(default_branch, str) and default_branch.strip():
            return default_branch.strip()
        return "main"

    @staticmethod
    def _job_names(jobs: list[dict[str, Any]]) -> list[str]:
        names: list[str] = []
        for job in jobs:
            name = job.get("name")
            if isinstance(name, str) and name:
                names.append(name)
        return names

    @staticmethod
    def _step_names(jobs: list[dict[str, Any]]) -> list[str]:
        names: list[str] = []
        for job in jobs:
            steps = job.get("steps")
            if not isinstance(steps, list):
                continue
            for step in steps:
                if not isinstance(step, dict):
                    continue
                name = step.get("name")
                if isinstance(name, str) and name:
                    names.append(name)
        return names

    def _create_disposable_pull_request(self, default_branch: str) -> _DisposablePullRequest:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts131-pr-"))
        branch_name = self._build_branch_name()
        pull_request_title = (
            f"TS-131 disposable probe: block non-tokenized color ({branch_name})"
        )
        branch_pushed = False

        try:
            self._clone_repository(temp_repository_root)
            self._run_git(
                temp_repository_root,
                "checkout",
                "-b",
                branch_name,
                f"origin/{default_branch}",
            )
            login = self._authenticated_login()
            self._run_git(temp_repository_root, "config", "user.name", login)
            self._run_git(
                temp_repository_root,
                "config",
                "user.email",
                f"{login}@users.noreply.github.com",
            )

            probe_path = temp_repository_root / self._config.probe_relative_path
            probe_path.parent.mkdir(parents=True, exist_ok=True)
            probe_path.write_text(self._probe_source(), encoding="utf-8")

            self._run_git(temp_repository_root, "add", self._config.probe_relative_path)
            self._run_git(
                temp_repository_root,
                "commit",
                "-m",
                "TS-131 disposable PR probe for theme-token CI",
            )
            commit_sha = self._run_git(
                temp_repository_root,
                "rev-parse",
                "HEAD",
            ).strip()
            self._run_git(
                temp_repository_root,
                "push",
                "--set-upstream",
                "origin",
                branch_name,
            )
            branch_pushed = True

            pull_request = self._read_json_object(
                f"/repos/{self._config.repository}/pulls",
                method="POST",
                stdin_json={
                    "title": pull_request_title,
                    "head": branch_name,
                    "base": default_branch,
                    "body": (
                        "Disposable TS-131 automation probe. This PR intentionally "
                        "adds a hardcoded Flutter color so CI should fail at the "
                        "theme-token gate."
                    ),
                },
            )
            pull_request_number = pull_request.get("number")
            if not isinstance(pull_request_number, int):
                raise ThemeTokenCiError(
                    "GitHub did not return a numeric Pull Request number for the "
                    f"disposable TS-131 branch {branch_name}."
                )
            return _DisposablePullRequest(
                temp_repository_root=temp_repository_root,
                branch_name=branch_name,
                commit_sha=commit_sha,
                pull_request_number=pull_request_number,
                pull_request_url=str(pull_request.get("html_url", "")),
                pull_request_title=str(pull_request.get("title", pull_request_title)),
                probe_relative_path=self._config.probe_relative_path,
            )
        except Exception:
            if branch_pushed:
                try:
                    self._github_api_client.request_text(
                        endpoint=(
                            f"/repos/{self._config.repository}/git/refs/heads/"
                            f"{quote(branch_name, safe='')}"
                        ),
                        method="DELETE",
                    )
                except GitHubApiClientError:
                    pass
            shutil.rmtree(temp_repository_root, ignore_errors=True)
            raise

    def _cleanup_disposable_pull_request(
        self,
        disposable_pull_request: _DisposablePullRequest,
    ) -> None:
        errors: list[str] = []
        try:
            self._read_json_object(
                f"/repos/{self._config.repository}/pulls/"
                f"{disposable_pull_request.pull_request_number}",
                method="PATCH",
                stdin_json={"state": "closed"},
            )
        except ThemeTokenCiError as error:
            errors.append(f"closing PR failed: {error}")

        try:
            self._github_api_client.request_text(
                endpoint=(
                    f"/repos/{self._config.repository}/git/refs/heads/"
                    f"{quote(disposable_pull_request.branch_name, safe='')}"
                ),
                method="DELETE",
            )
        except GitHubApiClientError as error:
            if "HTTP 404" not in str(error):
                errors.append(f"deleting branch failed: {error}")

        shutil.rmtree(disposable_pull_request.temp_repository_root, ignore_errors=True)
        if errors:
            raise ThemeTokenCiError(
                "TS-131 observed the disposable Pull Request but could not fully "
                "clean it up.\n"
                + "\n".join(errors)
            )

    def _clone_repository(self, destination: Path) -> None:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise ThemeTokenCiError(
                "TS-131 requires GH_TOKEN or GITHUB_TOKEN so the disposable Pull "
                "Request branch can be pushed to GitHub."
            )

        remote_url = f"https://x-access-token:{token}@github.com/{self._config.repository}.git"
        self._run_subprocess(
            (
                "git",
                "clone",
                "--quiet",
                "--no-tags",
                remote_url,
                str(destination),
            ),
            cwd=None,
            redactions=((token, "***"),),
        )

    def _run_git(self, repository_root: Path, *args: str) -> str:
        return self._run_subprocess(("git", *args), cwd=repository_root)

    def _run_subprocess(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path | None,
        redactions: tuple[tuple[str, str], ...] = (),
    ) -> str:
        environment = os.environ.copy()
        environment.setdefault("GH_PAGER", "cat")
        environment["GIT_TERMINAL_PROMPT"] = "0"
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            stdout = completed.stdout
            stderr = completed.stderr
            for secret, replacement in redactions:
                stdout = stdout.replace(secret, replacement)
                stderr = stderr.replace(secret, replacement)
            raise ThemeTokenCiError(
                f"{' '.join(command[:3])} failed with exit code {completed.returncode}.\n"
                f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            )
        return completed.stdout.strip()

    def _authenticated_login(self) -> str:
        user = self._read_json_object("/user")
        login = user.get("login")
        if not isinstance(login, str) or not login.strip():
            raise ThemeTokenCiError(
                "GitHub authentication did not return a usable login for TS-131."
            )
        return login.strip()

    def _build_branch_name(self) -> str:
        suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"{self._config.pull_request_branch_prefix}-{suffix}"

    def _probe_source(self) -> str:
        return """import 'package:flutter/material.dart';

class Ts131PullRequestProbe extends StatelessWidget {
  const Ts131PullRequestProbe({super.key});

  @override
  Widget build(BuildContext context) {
    return const ColoredBox(
      color: Color(0xFF000000),
      child: SizedBox(width: 16, height: 16),
    );
  }
}
"""

    def _read_json_object(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        field_args: list[str] | None = None,
        stdin_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = self._read_json(
            endpoint,
            method=method,
            field_args=field_args,
            stdin_json=stdin_json,
        )
        if not isinstance(payload, dict):
            raise ThemeTokenCiError(
                f"Expected a JSON object from gh api {endpoint}, got {type(payload)}."
            )
        return payload

    def _read_json(
        self,
        endpoint: str,
        *,
        method: str = "GET",
        field_args: list[str] | None = None,
        stdin_json: dict[str, Any] | None = None,
    ) -> object:
        try:
            response_text = self._github_api_client.request_text(
                endpoint=endpoint,
                method=method,
                field_args=field_args,
                stdin_json=stdin_json,
            )
        except GitHubApiClientError as error:
            raise ThemeTokenCiError(str(error)) from error
        return json.loads(response_text)

    @staticmethod
    def _optional_string(value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _run_created_at_epoch(run: dict[str, Any]) -> float | None:
        created_at = run.get("created_at")
        if not isinstance(created_at, str) or not created_at:
            return None
        try:
            return datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
